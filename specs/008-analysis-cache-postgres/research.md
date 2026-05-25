# Phase 0 — Research

**Feature**: 008 Postgres-backed analysis cache
**Date**: 2026-05-25

Six technical decisions locked before implementation.

---

## R1 — Postgres (not SQLite, not filesystem extension)

**Decision**: Postgres 17-alpine as the cache backend. Connection via SQLAlchemy 2.0 async + psycopg 3 driver. Schema managed by Alembic.

**Rationale**: Maintainer explicitly chose Postgres to consolidate the audit cache with the upcoming users / plans / subscriptions / billing tables (feature 009+). Using filesystem JSON or SQLite would force a second migration in 2-3 months when auth lands. Postgres also offers JSONB indexing, partial indexes, RLS for future multi-tenancy, and battle-tested concurrent UPSERTs.

**Alternatives Considered**:
- **Fix the existing filesystem cache** (`~/.cleanmatch/runs/<hash>/`): rejected. Would need re-migration to Postgres when auth lands. Two-phase work for no net gain.
- **SQLite**: rejected. No JSONB-indexed equivalent. Plus migration to Postgres needed for monetization stage anyway.
- **Redis / DynamoDB**: rejected. Cache is also the system-of-record for historical audit runs; needs durable relational storage.

---

## R2 — Composite cache key `(pgn_sha256, manifest_sha256)`

**Decision**: UNIQUE constraint on `(pgn_sha256, manifest_sha256)`. Lookup filters on both. Insert uses `ON CONFLICT DO NOTHING`.

**Rationale**:
- `pgn_sha256` is content-addressing — identical PGN bytes always map to the same key regardless of source platform.
- `manifest_sha256` (output of `manifest_hash()` at `packages/analysis-core/src/analysis_core/manifest.py:79`) covers engine binary sha256, opening book sha256, baselines version, signal versions, scoring threshold version. Algorithm bump → manifest_sha256 changes → automatic cache invalidation without manual purge.
- Composite UNIQUE allows two rows for the same PGN under different algorithm versions (useful for historical comparison + A/B testing scoring changes).

**Alternatives Considered**:
- **Platform game_id only** (e.g. `chess.com_<slug>`): rejected. Doesn't capture algorithm version; serving a stale row after an algorithm bump produces silently-wrong scores.
- **Manifest hash alone**: rejected. Manifest includes per-run metadata (`started_at`, `host`) that's already stripped from `manifest_hash()`, but coupling primary key purely to manifest hash makes the lookup unintuitive ("look up by which PGN was analyzed").

---

## R3 — Pipeline-level integration (not Next.js /api/analyze)

**Decision**: Cache lookup happens in `packages/analysis-core/src/analysis_core/pipeline/run.py::run_single_game()` before engine spawn. Backend Next.js `/api/analyze` route stays a thin spawn-and-stream proxy.

**Rationale**:
- CLI users (`cleanmatch audit-game`) get the cache benefit too, not just frontend users.
- The frontend `/api/analyze` route already spawns `python lib/analyze.py` via subprocess — pushing cache logic into Python means a single integration point.
- The manifest-hash computation requires Python access to the heuristic versions, engine sha256, etc. — duplicating this in TypeScript would be a maintenance hazard.

**Alternatives Considered**:
- **TypeScript-side cache in Next.js**: rejected. Would need duplicated manifest computation in TS.
- **Postgres backend HTTP API in front of CLI**: rejected. Adds a new service to deploy; the CLI is the system-of-record.

---

## R4 — Graceful DB-down (warn + skip, no raise)

**Decision**: If `DATABASE_URL` is unset OR the database is unreachable, `db.cache.lookup()` logs `level=warning event=db.cache.disabled` to stderr and returns `None`. `db.cache.persist()` logs and no-ops. The audit pipeline proceeds normally.

**Rationale**:
- Developer machines without Postgres must continue to work (clone-and-go onboarding).
- Production resilience: a 30-second Postgres restart shouldn't break user-facing audits — just kill the cache for those 30 seconds.
- CLI exit-code contract (Principle III) requires that infrastructure issues don't surface as user-error exit codes.

**Alternatives Considered**:
- **Hard-fail on unreachable Postgres**: rejected — too brittle for developer experience.
- **Silently swallow + don't log**: rejected — operators need observability when the cache is offline (cost is real — full Stockfish runs every request).

---

## R5 — Async SQLAlchemy + psycopg3

**Decision**: `from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine`. Driver URL prefix `postgresql+psycopg://`. Lookup + persist are async functions.

**Rationale**:
- `run_single_game()` is already an async function in the existing pipeline. Sync DB calls would block the event loop; async preserves the streaming-audit semantics for the SSE proxy.
- psycopg 3 is the actively-maintained driver, with native async support (vs psycopg 2 which requires the `psycopg2-binary` + threadpool workaround).

**Alternatives Considered**:
- **Sync SQLAlchemy + threadpool**: rejected. Extra mental overhead with no win.
- **Raw asyncpg + hand-written SQL**: rejected. Loses Alembic integration and SQLAlchemy's UPSERT abstraction.

---

## R6 — Reserved `user_id` + `tenant_id` columns

**Decision**: `audit_runs` table includes `user_id UUID NULL` + `tenant_id UUID NULL` from `0001_init`, with no FK constraints. Feature 009 adds the `users` table and a deferred migration to attach FKs and backfill.

**Rationale**:
- ALTER TABLE ADD COLUMN UUID NULL is online-safe in Postgres 11+. Doing it preemptively avoids a future migration on a table that may have grown to gigabytes.
- Pre-allocating these columns signals intent + enables incremental rollout of auth without a coordinated schema cutover.
- The PR scope for feature 009 stays small: add `users` table, populate `user_id` on new inserts, add FK constraint as a separate Alembic step.

**Alternatives Considered**:
- **Wait until feature 009 to add the columns**: rejected. Re-tooling the cache layer in 2-3 months for an additive change is wasted effort.
- **Add NOT NULL with a default sentinel UUID**: rejected. Implies false ownership; NULL is the semantically correct "anonymous / pre-auth" state.
