# Clean Match Chess

Probabilistic fair-play audit platform for online chess.

[![CI](https://github.com/wellingtonpoll/clean-match-chess/actions/workflows/ci.yml/badge.svg)](https://github.com/wellingtonpoll/clean-match-chess/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/wellingtonpoll/clean-match-chess/branch/main/graph/badge.svg)](https://codecov.io/gh/wellingtonpoll/clean-match-chess)
[![mypy](https://img.shields.io/badge/mypy-strict-blue)](pyproject.toml)
[![ruff](https://img.shields.io/badge/ruff-clean-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

> **Forensic Analytics Design System v1.0.0** — palette, typography,
> motion, and lexical audits enforced in CI.

> **Status**: v2.0.0 (Scoring v2 Phase 1) shipped. Two delivery
> surfaces: CLI auditor + web SPA. Real opening book bundled; Phase 2
> rating-baseline regeneration tracked in feature 007.
> - Feature 001-fairplay-analysis: **103/103 done**. See
>   [`specs/001-fairplay-analysis/quickstart.md`](specs/001-fairplay-analysis/quickstart.md).
> - Feature 002-design-system: **v1.0.0 released**. See
>   [`specs/002-design-system/quickstart.md`](specs/002-design-system/quickstart.md)
>   and the package docs under
>   [`packages/design-system/docs/`](packages/design-system/docs/).
> - Feature 004-scoring-v2-phase1: **2.0.0 released** (breaking).
> - Feature 005-scoring-v2-phase2: **shipped** (real Polyglot book +
>   clean corpus + FPR-gate infra). Baselines + engine-assisted corpus
>   + measured FPR/TPR continue in feature 007.
> - Feature 006-frontend-ux-improvements: **shipped** (clickable player
>   links, expandable cards, sticky header, cross-viewport Playwright
>   suite, profile lockup, sticky hero, per-game reasoning narrative).

## Quickstart

- CLI auditor: [`specs/001-fairplay-analysis/quickstart.md`](specs/001-fairplay-analysis/quickstart.md)
- Frontend SPA: `cd apps/frontend && npm install && npm run dev` (Next.js
  15, consumes the CLI via the `/api/analyze` SSE proxy).
- Design system: [`specs/002-design-system/quickstart.md`](specs/002-design-system/quickstart.md)
- Contributor flow for design tokens, components, lexicon:
  [`packages/design-system/docs/CONTRIBUTING.md`](packages/design-system/docs/CONTRIBUTING.md)

```bash
git clone <repo>
cd clean-match-chess
uv sync
uv run cleanmatch --help
```

**Requirements**: Python 3.11+, [Stockfish 16+](https://stockfishchess.org/download/),
[Postgres 14+](https://www.postgresql.org/) (optional — analysis cache; degrades gracefully when absent), Node 20+ (for the frontend SPA).

## Frontend dev (feature 012 orchestrator)

```bash
./scripts/dev.sh
```

Single command that boots Postgres, applies migrations, cleans zombie Stockfish containers, starts the audit worker daemon in the background, and launches the Next.js dev server on `http://localhost:3000`. Ctrl-C tears everything down except Postgres (which persists its data volume).

Override the pool / engine config inline:

```bash
CLEANMATCH_POOL_SIZE=2 CLEANMATCH_ENGINE_DEPTH=8 ./scripts/dev.sh
```

The frontend's audit pipeline depends on the worker process — without `dev.sh` (or starting `apps/frontend/lib/audit_worker.py` manually), submitted audits queue forever and the UI shows "pending" indefinitely. Feature 012 adds a health endpoint + UI banner that detects worker-offline.

## Database (feature 008 — analysis cache)

Identical PGN re-runs return in <1 s instead of 30–60 s once Postgres
is running. Cache is invisible to the user: `cleanmatch audit-game`
consults the DB before spawning Stockfish and persists the result after
analysis.

```bash
# Start the bundled Postgres
docker compose -f infra/docker/compose.yml up -d postgres
# or: podman compose -f infra/docker/compose.yml up -d postgres

# Apply schema
uv run alembic -c packages/analysis-core/alembic.ini upgrade head

# Set the connection URI for your shell (or copy .env.example to .env)
export DATABASE_URL=postgresql+psycopg://cleanmatch:cleanmatch@localhost:5432/cleanmatch
```

When `DATABASE_URL` is unset OR Postgres is unreachable, the audit runs
without caching and logs a structured warning. See
[`packages/analysis-core/docs/cache.md`](packages/analysis-core/docs/cache.md)
for the full ops runbook.

## Repository layout

```text
apps/cli/              # cleanmatch CLI (primary entry point)
apps/frontend/         # Next.js 15 SPA — search + per-game cards +
                       #                   profile lockup (feature 006)

packages/analysis-core # PGN ingest, engine pool, pipeline
packages/heuristics    # versioned signal modules + rating baselines
packages/report-engine # HTML/PDF/JSON renders
packages/shared-types  # Pydantic v2 schemas reused everywhere
packages/design-system # tokens, components, lexicon, 4 audits

infra/                 # Docker, compose
specs/                 # Spec Kit feature specifications (001-007)
tests/                 # cross-package fixtures + e2e + FPR-gate
```

## Constitution

Non-negotiables live in `.specify/memory/constitution.md`. Four
principles: code quality, testing (NON-NEGOTIABLE), UX consistency,
performance.

## Active features

- `specs/001-fairplay-analysis/` — MVP CLI auditor (shipped, 103/103).
- `specs/002-design-system/` — forensic-analytics design system v1.0.0
  (shipped). See [components catalogue](packages/design-system/docs/COMPONENTS.md),
  [lexicon](packages/design-system/docs/LEXICON.md), and
  [audits](packages/design-system/docs/AUDITS.md).
- `specs/003-repo-health-hardening/` — CI supply-chain hardening,
  community health files, Dependabot (shipped).
- `specs/004-scoring-v2-phase1/` — Fraud Detection Algorithm v2.0.0
  (breaking; shipped at `[2.0.0] — 2026-05-24`).
- `specs/005-scoring-v2-phase2/` — real Polyglot opening book + clean
  corpus + FPR-gate infra (shipped). Baselines + engine-assisted corpus
  carry over to feature 007.
- `specs/006-frontend-ux-improvements/` — Next.js SPA with US1-US4
  (clickable player links, expandable cards, sticky header,
  cross-viewport Playwright suite). Shipped at commit `211bf64`.
- `specs/007-scoring-v2-phase2-completion/` — closes feature 005's
  Pending stanza: measured rating baselines from Lichess 2026-04 dump
  + engine-assisted corpus + FPR-gate validation. **In flight** on
  branch `007-scoring-v2-phase2-completion`.

## License

[Apache 2.0](LICENSE)
