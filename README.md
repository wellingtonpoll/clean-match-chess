# Clean Match Chess

Probabilistic fair-play audit platform for online chess.

[![tests](https://img.shields.io/badge/tests-187%20passing-success)]()
[![coverage](https://img.shields.io/badge/coverage-90%25-success)]()
[![mypy](https://img.shields.io/badge/mypy-strict-blue)]()
[![ruff](https://img.shields.io/badge/ruff-clean-blue)]()
[![constitution](https://img.shields.io/badge/constitution-v1.0.0-informational)]()

> **Status**: Phase 1 MVP shippable. CLI-first; web platform deferred to Phase 3.
> Feature 001-fairplay-analysis tasks: **93/103 done** (Polish phase landing). See
> `specs/001-fairplay-analysis/tasks.md`.

## Quickstart

See [`specs/001-fairplay-analysis/quickstart.md`](specs/001-fairplay-analysis/quickstart.md)
for the canonical install + first-audit walkthrough.

```bash
git clone <repo>
cd clean-match-chess
uv sync
uv run cleanmatch --help
```

## Repository layout

```text
apps/cli/              # cleanmatch CLI (MVP entry point)
apps/api/              # Phase 3 placeholder
apps/frontend/         # Phase 3 placeholder

packages/analysis-core # PGN ingest, engine pool, pipeline
packages/heuristics    # versioned signal modules
packages/report-engine # HTML/PDF/JSON renders
packages/shared-types  # Pydantic v2 schemas reused everywhere

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
- `specs/002-design-system/` — forensic-analytics design system (extends
  the MVP report-engine).

## License

TBD.
