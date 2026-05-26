# Clean Match Chess

Probabilistic fair-play audit platform for online chess.

[![CI](https://github.com/wellingtonpoll/clean-match-chess/actions/workflows/ci.yml/badge.svg)](https://github.com/wellingtonpoll/clean-match-chess/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/wellingtonpoll/clean-match-chess/branch/main/graph/badge.svg)](https://codecov.io/gh/wellingtonpoll/clean-match-chess)
[![mypy](https://img.shields.io/badge/mypy-strict-blue)](pyproject.toml)
[![ruff](https://img.shields.io/badge/ruff-clean-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

> **Forensic Analytics Design System v1.0.0** — palette, typography,
> motion, and lexical audits enforced in CI.

> **Status**: Phase 1 MVP shippable. CLI-first; web platform deferred
> to Phase 3.
> - Feature 001-fairplay-analysis: **103/103 done**. See
>   [`specs/001-fairplay-analysis/quickstart.md`](specs/001-fairplay-analysis/quickstart.md).
> - Feature 002-design-system: **Phase 5 US3 landing**. See
>   [`specs/002-design-system/quickstart.md`](specs/002-design-system/quickstart.md)
>   and the package docs under
>   [`packages/design-system/docs/`](packages/design-system/docs/).

## Quickstart

- CLI auditor: [`specs/001-fairplay-analysis/quickstart.md`](specs/001-fairplay-analysis/quickstart.md)
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
[Postgres 14+](https://www.postgresql.org/) (optional — analysis cache; degrades gracefully when absent).

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
apps/cli/              # cleanmatch CLI (MVP entry point)
apps/api/              # Phase 3 placeholder
apps/frontend/         # Phase 3 placeholder

packages/analysis-core # PGN ingest, engine pool, pipeline
packages/heuristics    # versioned signal modules
packages/report-engine # HTML/PDF/JSON renders
packages/shared-types  # Pydantic v2 schemas reused everywhere
packages/design-system # tokens, components, lexicon, 4 audits

infra/                 # Docker, compose
specs/                 # Spec Kit feature specifications
tests/                 # cross-package fixtures + e2e
```

## Constitution

Non-negotiables live in `.specify/memory/constitution.md`. Four
principles: code quality, testing (NON-NEGOTIABLE), UX consistency,
performance.

## Active features

- `specs/001-fairplay-analysis/` — MVP CLI auditor.
- `specs/002-design-system/` — forensic-analytics design system. See
  [components catalogue](packages/design-system/docs/COMPONENTS.md),
  [lexicon](packages/design-system/docs/LEXICON.md), and
  [audits](packages/design-system/docs/AUDITS.md).

## License

[Apache 2.0](LICENSE)
