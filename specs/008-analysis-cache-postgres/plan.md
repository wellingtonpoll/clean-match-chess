# Implementation Plan: Postgres-backed analysis cache

**Branch**: `008-analysis-cache-postgres` | **Date**: 2026-05-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-analysis-cache-postgres/spec.md`

## Summary

Wire a Postgres-backed cache around `pipeline.run.run_single_game()` so identical PGN re-runs return in < 500 ms (vs 30-60 s for a cache miss). Cache key is `(pgn_sha256, manifest_sha256)` — the manifest hash automatically invalidates rows when the scoring algorithm or engine changes. Schema reserves nullable `user_id` + `tenant_id` columns for the incoming auth + subscriptions feature (009+).

## Technical Context

**Language/Version**: Python 3.12 (uv-managed workspace)

**Primary Dependencies**: `sqlalchemy >= 2.0` (declarative + async), `psycopg[binary] >= 3.2` (driver), `alembic >= 1.13` (migrations). All three pinned in `packages/analysis-core/pyproject.toml` `[project.dependencies]` (not `[optional]`) because the cache is a runtime concern when `DATABASE_URL` is set.

**Storage**: Postgres 17-alpine. Schema: single `audit_runs` table with `pgn_sha256 BYTEA`, `manifest_sha256 BYTEA`, `run_json JSONB`, `manifest_json JSONB`, UNIQUE constraint on `(pgn_sha256, manifest_sha256)`, four indexes for future query patterns, reserved `user_id` + `tenant_id` UUID columns.

**Testing**: pytest + sqlalchemy.ext.asyncio. Unit tests use SQLite-async in-memory where viable; integration tests at `tests/integration/test_postgres_cache.py` spin a real Postgres container via the existing `infra/docker/compose.yml`. CI's `test` job adds a `services: postgres` block.

**Target Platform**: Linux server / dev machine. Production runs Postgres ≥ 14 (for `gen_random_uuid()` via `pgcrypto`).

**Project Type**: Python monorepo with `packages/analysis-core` (cache lives here), `apps/cli` (CLI plumbs `--no-cache`).

**Performance Goals**:
- Cache hit p50 ≤ 100 ms wall-clock, p99 ≤ 500 ms.
- Cache miss preserves the current 30-60 s budget (no measurable overhead from the lookup + persist).
- Schema indexed for future per-user history queries; current usage hits the UNIQUE index for the lookup.

**Constraints**:
- Cannot break the `cleanmatch audit-game --output json` envelope shape (FR-007).
- Cannot hard-fail when `DATABASE_URL` is unset or the DB is unreachable (FR-004).
- No `users` table or FKs to it (out of scope — feature 009).

**Scale/Scope**:
- Initial expected row count: < 10k audits in the first 6 months.
- Per-row size: `run_json` ~50 KB + `manifest_json` ~2 KB ≈ 52 KB.
- 10k rows ≈ 520 MB on disk; well within commodity Postgres tunings.
- Forward path: at 100k rows (~5 GB), feature 010+ adds TTL pruning.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I — Code Quality**: PASS. SQLAlchemy 2.0 typed declarative + Alembic versioned migrations + mypy --strict + ruff. New code lives in a small `db/` submodule with narrow public API (`lookup`, `persist`, `init_engine`).
- **Principle II — Testing NON-NEGOTIABLE**: PASS. Unit tests with in-memory SQLite cover the cache layer hermetically. Integration tests with real Postgres validate the end-to-end path. Coverage gate `pytest --cov --cov-fail-under=85` enforced in Phase 7.
- **Principle III — UX Consistency**: PASS. CLI behavior preserved — exit codes unchanged, `--output json` envelope unchanged (FR-007), `--no-cache` flag finally honored (FR-003). Graceful degradation on DB-down emits to stderr per Principle III (not stdout).
- **Principle IV — Performance Requirements**: PASS. Cache miss preserves the existing per-ply engine-analysis budget (≤ 2.0 s/ply at depth 18). Cache hit improves wall-clock by ≥ 60× per SC-001. No regression risk; pipeline gating untouched.

**No violations. No complexity-tracking entries needed.**

## Project Structure

### Documentation (this feature)

```text
specs/008-analysis-cache-postgres/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 — decisions D1–D6
├── tasks.md             # Phase 2 — T001–T023
├── quickstart.md        # Phase 1 — recipes per phase
├── HANDOFF.md           # (none — no maintainer-machine action required this round)
├── contracts/           # (no new contracts; reuses ReproducibilityManifest)
└── checklists/
    └── requirements.md  # Spec quality gate
```

### Source Code (repository root)

```text
infra/docker/
├── compose.yml                          # +postgres service (new or extend)
├── postgres.Dockerfile                  # (optional) custom init scripts

packages/analysis-core/
├── pyproject.toml                       # +sqlalchemy, +psycopg, +alembic
├── alembic.ini                          # new — Alembic config
├── migrations/
│   ├── env.py                           # new — Alembic env (reads DATABASE_URL)
│   └── versions/
│       └── 0001_init.py                 # new — pgcrypto + audit_runs table
├── src/analysis_core/
│   ├── db/
│   │   ├── __init__.py                  # new — re-exports
│   │   ├── models.py                    # new — AuditRun SQLAlchemy model
│   │   ├── session.py                   # new — async engine + session factory
│   │   └── cache.py                     # new — lookup() + persist()
│   └── pipeline/
│       └── run.py                       # wire lookup + persist
├── tests/
│   └── test_db_cache.py                 # new — unit tests (in-memory SQLite)

apps/cli/src/cleanmatch_cli/
├── main.py                              # plumb --no-cache through
└── commands/
    ├── audit_game.py                    # accept no_cache param
    └── audit_username.py                # accept no_cache param

tests/integration/
└── test_postgres_cache.py               # new — real Postgres E2E

.github/workflows/ci.yml                 # +services: postgres block
.env.example                             # new — DATABASE_URL template
```

**Structure Decision**: Small, additive scope. New `db/` submodule under `analysis-core`. Migrations live next to the package so `alembic.ini` can resolve them via relative path. CLI plumbing is 2 lines per command. No new packages, no new top-level directories.

## Complexity Tracking

*No violations. Section intentionally empty.*
