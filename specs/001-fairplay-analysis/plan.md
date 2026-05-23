# Implementation Plan: Probabilistic Fair Play Analysis Platform

**Branch**: `001-fairplay-analysis` | **Date**: 2026-05-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-fairplay-analysis/spec.md`

## Summary

Phase 1 MVP delivers a **command-line probabilistic fair-play auditor** for
chess.com PGNs. The pipeline ingests one game (or a batch fetched by public
username), runs deterministic Stockfish analysis at pinned settings, computes
versioned heuristic signals (engine correlation, complexity-weighted match,
behavioral regime shifts, timing anomalies), aggregates a suspicion score with
a confidence interval and a categorical risk level, and emits a reproducible
report bundle (PDF + JSON + manifest) with per-move explainability.

The eventual full platform is web-based (FastAPI + Next.js + Dramatiq workers,
per user input on /speckit-plan), but those layers are explicitly deferred to
Phase 3. The MVP keeps the same monorepo structure so the analysis core and
heuristics packages are reused unchanged by the future API and worker apps.

## Technical Context

**Language/Version**: Python 3.11 (CLI, analysis core, heuristics, report
engine). TypeScript 5.x reserved for the Phase 3 Next.js frontend (not built
in this phase).

**Primary Dependencies**: `python-chess` (PGN/UCI/board), `stockfish` (binary
16+ invoked via UCI), `pydantic` v2 (typed schemas), `typer` (CLI), `httpx`
(chess.com Public API), `jinja2` + `weasyprint` (PDF rendering),
`structlog` (structured logging). Phase 3 only: `fastapi`, `dramatiq[redis]`,
`sqlalchemy` 2.x, `alembic`, `next`, `tailwindcss`, `echarts`, `auth.js`.

**Storage**: Local filesystem under `~/.cleanmatch/` in MVP (raw PGN cache,
analysis JSON, exported reports). PostgreSQL + MinIO planned for Phase 3.

**Testing**: `pytest` + `pytest-cov` (coverage gate 85% line / 80% branch on
`packages/*/src/`). Fixture PGNs and pinned Stockfish output checked into
`tests/fixtures/`. `pytest-benchmark` for performance budgets.

**Target Platform**: Linux + macOS developer workstations (x86_64 reference).
CLI distributed as a `pipx`-installable package; container image for
reproducible runs.

**Project Type**: Monorepo (Python uv workspace) — `apps/cli` consumes
`packages/analysis-core`, `packages/heuristics`, `packages/report-engine`,
`packages/shared-types`. `apps/api` and `apps/frontend` exist as empty
placeholders for Phase 3.

**Performance Goals** (binding per constitution Principle IV):

- Engine analysis ≤ 2.0 s wall-clock per ply at depth 18 on the reference
  machine (8 cores, Stockfish 16, single thread per game).
- Game ingest ≤ 5 s for 100 games from chess.com, including 429 backoff.
- Report render ≤ 3 s p95 HTML, ≤ 8 s p95 PDF for a 50-game report.
- Memory ≤ 1.5 GB RSS for a 200-game single-username analysis.
- Single-game end-to-end ≤ 5 min wall-clock for an 80-ply game (matches
  spec SC-001).

**Constraints**:

- Determinism is non-negotiable: Stockfish invocations pin depth, threads,
  hash, MultiPV, and seed-equivalents; identical inputs MUST yield bit-
  identical outputs (spec FR-017, constitution Principle II).
- No PGN, username, or analysis artifact leaves the user's machine in MVP
  (spec FR-018).
- No accusatory language in any output (spec FR-019, constitution
  Principle III).

**Scale/Scope**:

- Single-user single-machine in MVP. Up to 200 games per audit run.
- ~6 heuristic packages, ~5 game phases, ~20 named signals expected by end
  of Phase 2.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.0.0.

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I   | Code Quality           | ✅ PASS | `ruff` + `ruff format` + `mypy --strict` wired into CI. Public surface (CLI flags, package functions) typed and docstring-required. |
| II  | Testing Standards      | ✅ PASS | Every heuristic gets unit tests with pinned PGN/Stockfish fixtures. CLI e2e covers single-game and username-batch paths on a known-clean + known-suspect pair. Coverage gate 85/80 enforced. Red→green discipline applies to all signal modules. |
| III | UX Consistency         | ✅ PASS | CLI exit codes 0/1/2/3 standardized. `--output json` to stdout, human to stderr. `--log-format=json` and `--log-level` + `CLEANMATCH_LOG_LEVEL` env. Kebab-case subcommands. Errors carry actionable next-step guidance. |
| IV  | Performance Reqs       | ✅ PASS | Budgets above are tracked. PR template requires a benchmark or budget-change justification for changes under `packages/heuristics`, `packages/analysis-core`, or `packages/report-engine`. Bench harness lives under `packages/*/benchmarks/`. |

No principle violations. **Complexity Tracking table is empty.**

## Project Structure

### Documentation (this feature)

```text
specs/001-fairplay-analysis/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 — stack decisions, alternatives
├── data-model.md        # Phase 1 — entities and relationships
├── quickstart.md        # Phase 1 — local install + first audit
├── contracts/           # Phase 1 — CLI command schemas
│   ├── cli-audit-game.md
│   ├── cli-audit-username.md
│   ├── cli-show.md
│   └── cli-export.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # (NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/
├── cli/                            # MVP entry point — typer-based CLI
│   ├── pyproject.toml
│   ├── src/cleanmatch_cli/
│   │   ├── __init__.py
│   │   ├── main.py                 # typer app, top-level commands
│   │   ├── commands/
│   │   │   ├── audit_game.py       # cleanmatch audit-game …
│   │   │   ├── audit_username.py   # cleanmatch audit-username …
│   │   │   ├── show.py             # cleanmatch show <run-id>
│   │   │   └── export.py           # cleanmatch export <run-id> --pdf …
│   │   ├── output/                 # human + JSON renderers, exit-code map
│   │   └── config.py
│   └── tests/
│       ├── contract/               # CLI flag/JSON-schema contract tests
│       ├── integration/            # end-to-end against fixture PGNs
│       └── unit/
│
├── api/                            # Phase 3 placeholder — empty pyproject only
└── frontend/                       # Phase 3 placeholder

packages/
├── analysis-core/                  # ingest + engine + pipeline orchestration
│   ├── pyproject.toml
│   ├── src/analysis_core/
│   │   ├── ingest/
│   │   │   ├── pgn_loader.py       # FR-001, FR-003
│   │   │   └── chesscom_client.py  # FR-002 (public API only, with 429 backoff)
│   │   ├── engine/
│   │   │   ├── stockfish_pool.py   # multi-worker pool, deterministic settings
│   │   │   ├── uci.py              # low-level UCI wrapper around python-chess
│   │   │   └── analysis.py         # FR-004 — depth-pinned MultiPV
│   │   ├── pipeline/
│   │   │   ├── run.py              # AuditRun orchestrator
│   │   │   ├── segmentation.py     # FR-007 — phase + regime detection
│   │   │   └── cache.py            # deterministic cache keyed by manifest
│   │   └── manifest.py             # FR-015 — reproducibility manifest
│   └── tests/
│
├── heuristics/                     # versioned signal modules (DRS §10)
│   ├── pyproject.toml
│   ├── src/heuristics/
│   │   ├── registry.py             # versioned signal registry
│   │   ├── engine_correlation/     # FR-008, FR-009
│   │   ├── complexity_analysis/    # FR-006
│   │   ├── tactical_detection/     # FR-005
│   │   ├── behavioral_patterns/    # FR-010
│   │   ├── regime_shift/           # FR-007
│   │   ├── timing_analysis/        # FR-010 timing subset
│   │   └── scoring/                # FR-011 — aggregator + risk classifier
│   └── tests/                      # per-signal unit tests with pinned fixtures
│
├── report-engine/                  # FR-014 — HTML + PDF + JSON
│   ├── pyproject.toml
│   ├── src/report_engine/
│   │   ├── render_html.py          # Jinja2 templates
│   │   ├── render_pdf.py           # WeasyPrint
│   │   ├── render_json.py
│   │   ├── narrative.py            # FR-012 — plain-language captions
│   │   └── templates/
│   └── tests/                      # golden-file diff tests
│
└── shared-types/                   # Pydantic v2 schemas reused everywhere
    ├── pyproject.toml
    ├── src/shared_types/
    │   ├── game.py
    │   ├── position.py
    │   ├── signal.py
    │   ├── score.py
    │   ├── audit_run.py
    │   └── report.py
    └── tests/

infra/
├── docker/
│   ├── stockfish.Dockerfile        # pinned Stockfish 16 image
│   └── cleanmatch.Dockerfile       # CLI image
└── compose/
    └── dev.yml                     # local Redis/Postgres for Phase 3 prep
                                    # (not required by MVP CLI)

tests/                              # cross-package contract & e2e fixtures
├── fixtures/
│   ├── pgn/known-clean/
│   ├── pgn/known-suspect/
│   └── stockfish/                  # pinned engine output snapshots
└── e2e/

pyproject.toml                      # workspace root (uv)
uv.lock
```

**Structure Decision**: Monorepo Python workspace (uv) following the layout
the user prescribed in `/speckit-plan` input — `apps/{cli,api,frontend}` for
runnable entry points, `packages/{analysis-core,heuristics,report-engine,
shared-types}` for reusable logic, `infra/` for container/compose, `specs/`
for governance.

The MVP builds and ships only `apps/cli` plus the four `packages/`. `apps/api`
and `apps/frontend` exist as empty placeholders so Phase 3 work doesn't need
to reshape the tree. The signal package layout mirrors DRS §10 exactly so the
ontology stays one-to-one between docs and code.

## Constitution Check (Post-Design)

After laying out Phase 0 / Phase 1 artifacts, re-evaluation:

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I   | Code Quality           | ✅ PASS | Each package gets its own `pyproject.toml` with shared `ruff`/`mypy` config from root. Public APIs in `shared-types` are Pydantic models — typed by construction. |
| II  | Testing Standards      | ✅ PASS | Test plan in `tests/` + per-package `tests/` directory. Pinned engine fixtures + golden-file report diffs. Coverage gate stays. |
| III | UX Consistency         | ✅ PASS | CLI contract files in `contracts/` lock exit codes, output formats, flag grammar. |
| IV  | Performance Reqs       | ✅ PASS | Engine pool design (Stockfish-per-worker, deterministic settings) plus the cache module make budgets attainable. Benchmark harness has a home in each package's `benchmarks/`. |

No new violations introduced. **Complexity Tracking remains empty.**

## Complexity Tracking

> No constitution violations to justify.

(Empty.)
