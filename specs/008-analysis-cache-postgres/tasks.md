# Tasks — Feature 008 (Postgres-backed analysis cache)

**Input**: spec.md + plan.md + research.md (D1–D6)

**Prerequisites**:
- Docker available locally (compose engine ≥ 2.0)
- Python 3.12 (uv-managed)
- Postgres 17-alpine pulled OR network access to pull it

**Tests statement**: Unit tests with in-memory SQLite cover the cache layer hermetically; integration tests with real Postgres validate the end-to-end pipeline. `pytest --cov --cov-fail-under=85` enforced in Phase 7.

**Organization rules**:
- `[P]` = parallel-safe with other `[P]` tasks
- `⇐ TNNN` = depends on the named task
- `[X]` once completed

---

## Phase 0 — Setup

- [X] **T001** Branch + spec scaffold. `git worktree add -b 008-analysis-cache-postgres /tmp/cmc-008 main`. Created `specs/008-analysis-cache-postgres/{spec.md, plan.md, research.md, tasks.md, quickstart.md, contracts/, checklists/}`.

## Phase 1 — Infra

- [ ] **T002** [P] Add Postgres service to `infra/docker/compose.yml`. Service name `postgres`, image `postgres:17-alpine`, env vars `POSTGRES_USER=cleanmatch`, `POSTGRES_PASSWORD=cleanmatch`, `POSTGRES_DB=cleanmatch`, healthcheck `pg_isready -U cleanmatch`, port `5432:5432`, named volume `cleanmatch_pg_data`. Add brief `infra/docker/README.md` covering compose up/down + volume location.
- [ ] **T003** [P] `.env.example` at repo root. Documents `DATABASE_URL=postgresql+psycopg://cleanmatch:cleanmatch@localhost:5432/cleanmatch` + `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` for compose. Add `.env` to `.gitignore` (already there).
- [ ] **T004** [P] `packages/analysis-core/pyproject.toml` — add to `[project.dependencies]`:
  - `sqlalchemy >= 2.0, < 3`
  - `psycopg[binary] >= 3.2, < 4`
  - `alembic >= 1.13, < 2`
  Run `uv sync --all-packages --all-extras`.
- [ ] **T005** [⇐ T004] `packages/analysis-core/alembic.ini` — alembic configuration. `script_location = migrations`. `sqlalchemy.url` left blank — `env.py` reads from environment.
- [ ] **T006** [⇐ T005] `packages/analysis-core/migrations/env.py` — read `DATABASE_URL` from environment, fall back to dev default. Wire up sqlalchemy `MetaData` from `analysis_core.db.models.Base.metadata` (model created in T010).

## Phase 2 — Schema

- [ ] **T007** [⇐ T006] Initial migration `packages/analysis-core/migrations/versions/0001_init.py`. Contents:
  ```python
  def upgrade():
      op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
      op.create_table("audit_runs", ...)  # 13 columns per spec
      op.create_unique_constraint("audit_runs_pgn_manifest_unique", "audit_runs",
                                  ["pgn_sha256", "manifest_sha256"])
      op.create_index("idx_audit_runs_platform_game", "audit_runs", ["platform", "game_id"])
      op.create_index("idx_audit_runs_white", "audit_runs", ["white_username"])
      op.create_index("idx_audit_runs_black", "audit_runs", ["black_username"])
      op.create_index("idx_audit_runs_created", "audit_runs", ["created_at"], postgresql_using="btree")

  def downgrade():
      op.drop_index("idx_audit_runs_created", "audit_runs")
      op.drop_index("idx_audit_runs_black", "audit_runs")
      op.drop_index("idx_audit_runs_white", "audit_runs")
      op.drop_index("idx_audit_runs_platform_game", "audit_runs")
      op.drop_constraint("audit_runs_pgn_manifest_unique", "audit_runs")
      op.drop_table("audit_runs")
      op.execute("DROP EXTENSION IF EXISTS pgcrypto")
  ```
- [ ] **T008** [⇐ T007] Verify `alembic upgrade head` + `alembic downgrade base` round-trip cleanly. Run against a throwaway Postgres database. SC-005 acceptance.

## Phase 3 — DB layer

- [ ] **T009** [⇐ T004] `packages/analysis-core/src/analysis_core/db/__init__.py` — public API surface: re-export `lookup`, `persist`, `init_engine`, `AuditRunModel`.
- [ ] **T010** [⇐ T009] `packages/analysis-core/src/analysis_core/db/models.py` — `Base = declarative_base()` + `class AuditRunModel(Base)`. Columns match the `0001_init` schema. `__table_args__` carries the UNIQUE constraint + 4 indexes for SQLAlchemy metadata parity.
- [ ] **T011** [⇐ T010] `packages/analysis-core/src/analysis_core/db/session.py`:
  - `_engine: AsyncEngine | None = None` (module-level singleton)
  - `_session_factory: async_sessionmaker | None = None`
  - `def init_engine(url: str | None = None) -> None`: parses `DATABASE_URL` env var if `url` is `None`. Creates engine + session factory. Idempotent.
  - `def get_session_factory() -> async_sessionmaker | None`: returns the factory, or `None` if `init_engine` failed silently (e.g. `DATABASE_URL` unset).
  - `def _mask_url(url: str) -> str`: redacts password component before logging.
- [ ] **T012** [⇐ T011] `packages/analysis-core/src/analysis_core/db/cache.py`:
  - `async def lookup(pgn_sha256: bytes, manifest_sha256: bytes) -> AuditRun | None`:
    1. Get session factory; if `None`, log debug + return None.
    2. Open async session, SELECT WHERE both keys match LIMIT 1.
    3. Catch `OperationalError`, log warning, return None.
    4. On hit: deserialize `run_json` via `AuditRun.model_validate()`, return.
  - `async def persist(audit_run: AuditRun, manifest: ReproducibilityManifest) -> None`:
    1. Get session factory; if `None`, log debug + return.
    2. Build `AuditRunModel` instance with all indexed columns.
    3. Use Postgres `insert().on_conflict_do_nothing(index_elements=["pgn_sha256", "manifest_sha256"])`.
    4. Commit + close session.
    5. Catch `OperationalError`, log warning, return.
- [ ] **T013** [⇐ T012] Unit tests `packages/analysis-core/tests/test_db_cache.py`:
  - Lookup miss returns None.
  - Lookup hit returns deserialized AuditRun.
  - Persist creates row.
  - Persist twice (same key) is idempotent (still one row, no IntegrityError surfacing).
  - DB-down on lookup → warning + None.
  - DB-down on persist → warning + no-op.
  Uses in-memory SQLite via `aiosqlite` for hermetic coverage where possible; falls back to Postgres for tests that exercise `JSONB`/`BYTEA` cast quirks.

## Phase 4 — Pipeline integration

- [ ] **T014** [⇐ T012] Add cache hooks to `packages/analysis-core/src/analysis_core/pipeline/run.py::run_single_game()`:
  ```python
  async def run_single_game(..., no_cache: bool = False) -> AuditRun:
      pgn_sha256 = hashlib.sha256(pgn_bytes).digest()
      preview_manifest = _build_preview_manifest(...)  # engine sha, heuristics, etc.
      manifest_sha256 = bytes.fromhex(manifest_hash(preview_manifest))

      if not no_cache:
          cached = await db.cache.lookup(pgn_sha256, manifest_sha256)
          if cached is not None:
              return cached

      audit_run = await _run_engine_pipeline(...)  # existing path

      if not no_cache:
          await db.cache.persist(audit_run, audit_run.manifest)

      return audit_run
  ```
- [ ] **T015** [⇐ T014] Same hook pattern for `run_username_batch()` — apply per-game cache lookup inside the SSE-yielding loop.
- [ ] **T016** [⇐ T014] Plumb `--no-cache` through:
  - `apps/cli/src/cleanmatch_cli/main.py` — the flag is already defined; pass to execute().
  - `apps/cli/src/cleanmatch_cli/commands/audit_game.py::execute(..., no_cache: bool)` → `run_single_game(..., no_cache=no_cache)`.
  - `apps/cli/src/cleanmatch_cli/commands/audit_username.py::execute(..., no_cache: bool)` → `run_username_batch(..., no_cache=no_cache)`.

## Phase 5 — Integration tests + CI

- [ ] **T017** [⇐ T015] `tests/integration/test_postgres_cache.py`:
  - Fixture `postgres_session` spins compose service if not running.
  - Fixture `migrated_db` runs `alembic upgrade head` against the test DB.
  - `test_double_audit_hits_cache`: audit `audit_v2_smoke.pgn` twice. Assert second call wall-clock < 500 ms AND `audit_runs.count() == 1` AND JSON envelopes are identical modulo `run.id` + `started_at`.
  - `test_no_cache_flag_skips_persist`: with one cached row, run `cleanmatch audit-game --no-cache`. Assert row count unchanged.
  - `test_db_down_graceful`: with `DATABASE_URL` pointed at unreachable host, run audit. Assert exit 0 + JSON envelope present + warning emitted to stderr.
  - `test_migration_roundtrip`: `alembic upgrade head` + `alembic downgrade base` on a clean throwaway DB. Assert `pg_database` shows no `audit_runs`, `pgcrypto` dropped.
- [ ] **T018** [⇐ T017] `.github/workflows/ci.yml` — `test` job gains:
  ```yaml
  services:
    postgres:
      image: postgres:17-alpine
      env:
        POSTGRES_USER: cleanmatch
        POSTGRES_PASSWORD: cleanmatch
        POSTGRES_DB: cleanmatch
      ports:
        - 5432:5432
      options: >-
        --health-cmd "pg_isready -U cleanmatch"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
  ```
  Plus a step before `pytest`:
  ```yaml
  - name: Apply migrations
    env:
      DATABASE_URL: postgresql+psycopg://cleanmatch:cleanmatch@localhost:5432/cleanmatch
    run: uv run alembic -c packages/analysis-core/alembic.ini upgrade head
  ```

## Phase 6 — Docs

- [ ] **T019** `packages/analysis-core/docs/cache.md` — schema diagram, env vars, ops runbook (how to nuke + rebuild, how to bypass via `--no-cache`, retention policy stub).
- [ ] **T020** `CHANGELOG.md` — `## [Unreleased]` gains a new `### Added — Feature 008 (Postgres-backed analysis cache)` block above the feature-006 follow-up. Includes:
  - schema description (audit_runs table, key columns, indexes)
  - cache key strategy (`(pgn_sha256, manifest_sha256)`)
  - reserved `user_id` + `tenant_id` columns
  - `--no-cache` finally wired
  - graceful degradation when Postgres unreachable
  Cut `## [2.2.0] — <today>` header.
- [ ] **T021** `README.md` — under Requirements add "Postgres 14+ (optional — cache is graceful-degrading)". Add a "Database" subsection to Quickstart:
  ```bash
  docker compose -f infra/docker/compose.yml up -d postgres
  uv run alembic -c packages/analysis-core/alembic.ini upgrade head
  ```

## Phase 7 — Polish + PR

- [ ] **T022** `uv run ruff check . && uv run ruff format --check .` clean.
- [ ] **T023** `uv run mypy --strict packages/analysis-core/src` clean.
- [ ] **T024** `uv run pytest --cov --cov-fail-under=85` green (including new integration tests).
- [ ] **T025** End-to-end verification per `quickstart.md` on a fresh checkout. Document any deviations in PR description.
- [ ] **T026** Open PR. Labels: `infra`, `scoring`. Body describes schema design, future-proofing for auth, graceful degradation contract.

---

## Checkpoints

After Phase 2 (T008): schema migrates cleanly. Manual `psql -c "\d audit_runs"` shows expected columns including reserved `user_id` + `tenant_id`.

After Phase 4 (T016): pipeline + CLI integrate cleanly. Local test: `time cleanmatch audit-game audit_v2_smoke.pgn` twice — second call ≪ first.

After Phase 5 (T018): CI green on PR. Integration tests pass against real Postgres in GitHub Actions.

After Phase 7 (T026): PR open, merge candidate.
