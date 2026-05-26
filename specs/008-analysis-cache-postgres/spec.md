# Feature Specification: Postgres-backed analysis cache

**Feature Branch**: `008-analysis-cache-postgres`

**Created**: 2026-05-25

**Status**: Draft

**Input**: User description: "Implementar persistência das análises em Postgres — backend antes de realizar a análise consulta o banco; se já existe o ID da partida, traz os dados do banco em vez de reanalisar. Postgres porque em breve vai entrar autenticação + assinatura recorrente."

## Context

Running `cleanmatch audit-game` on the same PGN today re-runs the entire Stockfish pipeline (5-30 minutes per game depending on length). The existing filesystem cache at `~/.cleanmatch/runs/<manifest-hash>/` (in `packages/analysis-core/src/analysis_core/pipeline/cache.py`) writes the full audit artefacts but the lookup function `is_cached(manifest)` is NEVER called by the CLI — both `audit_game.execute()` and `audit_username.execute()` invoke `run_single_game()` / `run_username_batch()` directly. The CLI's `--no-cache` flag is accepted but ignored.

Maintainer strategic decision: instead of wiring the filesystem cache, jump straight to Postgres. Auth + recurring-subscription monetization is the next planned feature; consolidating audit cache + future users/plans/subscriptions in one database saves a deploy hop and avoids dual-storage complexity later.

## Clarifications

### Session 2026-05-25 (pre-plan)

- **Q**: Storage scope — local filesystem cache, SQLite, or Postgres? **A**: Postgres — pre-stages the auth + subscriptions database needed for the upcoming monetization feature.
- **Q**: Frontend history page? **A**: No. Cache must be invisible: backend consults DB before analysis; if game ID exists, return cached data without re-analyzing. No UI change.
- **Q**: Where does the lookup happen — Next.js `/api/analyze` route or Python pipeline? **A**: Python pipeline (`run_single_game()`). Benefits both CLI users and the frontend uniformly, since the SSE proxy spawns the CLI.

## User Scenarios & Testing *(mandatory)*

### User Story A — Identical PGN re-runs return instantly (Priority: P1)

A user (or the frontend SSE proxy) calls `cleanmatch audit-game PGN_X.pgn` once and waits 30-60 seconds for the Stockfish analysis. A second invocation of the same command on the same PGN returns the same scored result in under 100 ms because the audit run is fetched from Postgres rather than re-computed.

**Why this priority**: P1 — this is the entire point of the feature. Without it the user request is unmet.

**Independent Test**: `time cleanmatch audit-game audit_v2_smoke.pgn` twice in a row; second call must complete in <500 ms wall-clock and produce identical JSON output modulo `run.id` and `started_at`.

**Acceptance Scenarios**:

1. **Given** a fresh Postgres instance with the `0001_init` migration applied, **When** the maintainer runs `cleanmatch audit-game audit_v2_smoke.pgn` for the first time, **Then** the command completes in ~30-60 s (real Stockfish analysis), the resulting AuditRun is persisted to the `audit_runs` table with the correct `pgn_sha256`, `manifest_sha256`, `score`, `risk_level`, and `run_json` fields, and the JSON output to stdout is unchanged from the current implementation.
2. **Given** an entry exists in `audit_runs` matching the input PGN's sha256 AND the current manifest sha256, **When** the maintainer re-runs `cleanmatch audit-game audit_v2_smoke.pgn`, **Then** the command completes in under 500 ms wall-clock, no Stockfish process is spawned, and the JSON output matches the first run modulo `run.id` and `started_at`.
3. **Given** an entry exists in `audit_runs` for the same PGN BUT with a different `manifest_sha256` (e.g. opening book or scoring algorithm version changed since), **When** the maintainer re-runs the audit, **Then** the cache LOOKUP misses, full analysis runs, and a NEW row is inserted with the new manifest_sha256 (the old row is preserved for historical comparison).
4. **Given** the frontend SSE proxy calls `cleanmatch audit-game` via the existing `/api/analyze` route, **When** the underlying PGN matches a cached row, **Then** the SSE stream emits the cached AuditRun in a single event within ~500 ms total wall-clock from request start.

---

### User Story B — `--no-cache` flag finally works (Priority: P2)

The previously-fake `--no-cache` flag is wired to actually bypass both the cache lookup AND the persist step.

**Why this priority**: P2 — necessary for development / debugging (a maintainer hunting a bug in the scoring algorithm wants to force re-analysis without first manually clearing rows).

**Independent Test**: With a cached row present, `cleanmatch audit-game --no-cache audit_v2_smoke.pgn` must spawn Stockfish and complete in ~30-60 s. The cached row count in `audit_runs` must remain at 1 (no second row inserted).

**Acceptance Scenarios**:

1. **Given** an entry exists in `audit_runs` for `audit_v2_smoke.pgn`, **When** the maintainer runs `cleanmatch audit-game --no-cache audit_v2_smoke.pgn`, **Then** the command spawns Stockfish, completes in ~30-60 s, and the `audit_runs` row count is unchanged (`--no-cache` skips persist too).
2. **Given** no entry exists for a PGN, **When** the maintainer runs `cleanmatch audit-game --no-cache new_game.pgn`, **Then** the command runs full analysis and does NOT insert a row.

---

### User Story C — Graceful degradation when Postgres is unreachable (Priority: P1)

If `DATABASE_URL` is unset OR Postgres is unreachable (down, DNS failure, wrong credentials), the audit must still complete — it simply runs without caching and logs a structured warning.

**Why this priority**: P1 — the CLI must not become unusable on developer machines that don't have a database running, nor in environments where the DB is temporarily down.

**Independent Test**: With `DATABASE_URL` unset, `cleanmatch audit-game audit_v2_smoke.pgn` must complete successfully (exit 0) with full Stockfish analysis. A structured warning must be emitted to stderr (not stdout, per Principle III). Same behavior with `DATABASE_URL` set to an unreachable host.

**Acceptance Scenarios**:

1. **Given** the environment has no `DATABASE_URL` set, **When** the maintainer runs `cleanmatch audit-game audit_v2_smoke.pgn`, **Then** the command completes successfully, the audit runs at full cost, a structured warning is emitted to stderr (`level=warning event=db.cache.disabled reason=no-database-url`), and stdout JSON is identical to the pre-feature behavior.
2. **Given** `DATABASE_URL` points at a host on port 5432 that is not running Postgres, **When** the maintainer runs an audit, **Then** the same graceful path activates: warning emitted, analysis runs, exit 0.

---

### User Story D — Reserved auth + subscription columns (Priority: P2)

The `audit_runs` table includes nullable `user_id UUID` and `tenant_id UUID` columns from day one, even though no `users` table exists yet. Future feature 009+ can populate these columns via a deferred migration without restructuring the audit cache.

**Why this priority**: P2 — pure forward-compatibility; doesn't change any current behavior but prevents an expensive schema reshape later when auth + monetization land.

**Independent Test**: `psql $DATABASE_URL -c "\d audit_runs"` shows `user_id` and `tenant_id` columns, both `uuid` type, both nullable, no FK constraints (FKs added by feature 009 when `users` table exists).

**Acceptance Scenarios**:

1. **Given** the `0001_init` migration applied, **When** the maintainer inspects the `audit_runs` table schema, **Then** `user_id uuid` and `tenant_id uuid` are present with no NOT NULL constraint and no foreign-key constraints.
2. **Given** an INSERT from the cache layer does NOT supply `user_id` or `tenant_id`, **When** the row is persisted, **Then** it lands with both columns NULL — no constraint error.

---

### Edge Cases

- **Cache key collision** — two different PGNs producing identical sha256 is cryptographically impossible at SHA-256 strength; ignored as a risk.
- **Concurrent inserts of same `(pgn_sha256, manifest_sha256)`** — the UNIQUE constraint + `ON CONFLICT DO NOTHING` upsert prevents duplicate rows.
- **Postgres data loss** — losing the audit_runs table simply re-introduces the analysis cost for every PGN on next access. The filesystem cache at `~/.cleanmatch/runs/<hash>/` remains as a one-release fallback writer.
- **Schema migration on a running production database** — Alembic's transactional DDL handles this. Adding nullable columns is online-safe in Postgres ≥ 11.
- **Postgres version mismatch** — pinned at 17-alpine in `compose.yml`. Production must run ≥ 14 (for `gen_random_uuid()` via pgcrypto extension, available since 9.4).
- **JSONB blob inflation** — a typical `run_json` is ~50 KB. At 100k cached audits that's 5 GB. Document a retention-policy stub in `docs/cache.md`; feature 010+ can add TTL pruning.
- **`DATABASE_URL` containing the password leaked into logs** — `db/session.py` masks the password via `urllib.parse.urlsplit` before emitting any log line referencing the URI.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `pipeline.run.run_single_game()` MUST call `db.cache.lookup(pgn_sha256, manifest_sha256)` before spawning Stockfish. Cache hit → return cached `AuditRun` without engine work.
- **FR-002**: After a successful analysis (cache miss path), `pipeline.run.run_single_game()` MUST call `db.cache.persist(audit_run, manifest)` before returning.
- **FR-003**: The CLI `--no-cache` flag on `audit-game` and `audit-username` MUST cause the pipeline to skip BOTH lookup AND persist.
- **FR-004**: If the database is unreachable, `db.cache.lookup()` MUST log a structured warning to stderr and return `None`. `db.cache.persist()` MUST log + no-op. Neither raises an exception.
- **FR-005**: The `audit_runs` table MUST enforce `UNIQUE (pgn_sha256, manifest_sha256)`. Concurrent inserts MUST use `INSERT ... ON CONFLICT DO NOTHING`.
- **FR-006**: The `audit_runs` schema MUST include nullable `user_id UUID` and `tenant_id UUID` columns from `0001_init` with no FK constraints (reserved for feature 009+).
- **FR-007**: The cache layer MUST NOT change the JSON shape returned by `cleanmatch audit-game --output json`. Hit and miss produce the same envelope; consumers cannot detect cache state from the output.
- **FR-008**: Migrations MUST be reversible — `alembic upgrade head` followed by `alembic downgrade base` MUST leave the database in its pre-migration state.

### Key Entities *(include if feature involves data)*

- **`AuditRun` row** in `audit_runs`: primary persistence unit. One row per `(pgn_sha256, manifest_sha256)`. Carries the full `AuditRun` Pydantic envelope serialized as `run_json` plus indexed query columns for future history pages.
- **`ReproducibilityManifest`** (existing — `packages/analysis-core/src/analysis_core/manifest.py`): no schema change; the existing `manifest_hash()` function (line 79) is the canonical cache-key half.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A cached audit returns in **< 500 ms** wall-clock vs ~30-60 s for a cache miss on `audit_v2_smoke.pgn` (≥ 60× speedup).
- **SC-002**: `audit_runs` row count is exactly **1** after N consecutive runs of the same PGN (without `--no-cache`).
- **SC-003**: With `DATABASE_URL` unset OR pointing at an unreachable host, `cleanmatch audit-game audit_v2_smoke.pgn` exits 0 and produces correct JSON output (no degradation in functionality, only loss of cache).
- **SC-004**: The JSON envelope returned for a cache hit is **byte-identical** to the cache-miss output modulo `run.id` and `started_at` (and the manifest hash if recomputed).
- **SC-005**: `alembic upgrade head` followed by `alembic downgrade base` round-trips cleanly on an empty database with no orphan tables or columns.
- **SC-006**: The CI `test` job runs against a real Postgres service container; all cache tests pass.
- **SC-007**: A pre-PR `psql -c "\d audit_runs"` shows `user_id uuid` and `tenant_id uuid` nullable columns (forward-compat verified).

## Assumptions

- Maintainer machine + production environments either run Postgres ≥ 14 locally OR have `DATABASE_URL` unset (in which case the graceful-degradation path activates).
- Stockfish analysis dominates audit wall-clock (~30 s/game). Cache lookup overhead (~5 ms) is negligible.
- The `manifest_sha256` is already cheap to compute (it's a SHA-256 of 14 small fields per `manifest_hash()` at `packages/analysis-core/src/analysis_core/manifest.py:79`).
- The current AuditRun Pydantic envelope is serializable to JSONB via `.model_dump_json()` (round-trips cleanly via `.model_validate_json()`).
- Future auth (feature 009+) will own the `users` table; this feature only reserves the column.

## Constraints

- Cannot change the public JSON envelope returned by `cleanmatch audit-game --output json` (FR-007). Consumers + frontend depend on it.
- Cannot make the CLI hard-fail when Postgres is absent (FR-004). Developer machines must continue working without a running database.
- Cannot introduce a `users` table or any FK constraints involving `user_id` in this feature (out of scope).
- Schema must use Alembic for all changes; no `psql -c "ALTER TABLE ..."` hot-patches.

## Scope notes

- No frontend changes (FR-007 + maintainer's "sem página de histórico" direction).
- No scoring algorithm changes — cache is transparent to the analysis pipeline.
- No new CI workflow file; existing `test` job gains a postgres service.
- Filesystem cache at `~/.cleanmatch/runs/<hash>/` stays for one release as backup write-only target. A future feature can deprecate it once Postgres is steady-state.
