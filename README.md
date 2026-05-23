# Clean Match Chess

Probabilistic fair-play audit platform for online chess.

[![tests](https://img.shields.io/badge/tests-285%20passing-success)]()
[![coverage](https://img.shields.io/badge/coverage-93%25-success)]()
[![mypy](https://img.shields.io/badge/mypy-strict-blue)]()
[![ruff](https://img.shields.io/badge/ruff-clean-blue)]()
[![constitution](https://img.shields.io/badge/constitution-v1.0.0-informational)]()
[![design-system](https://img.shields.io/badge/design--system-v1.0.0-F4D21F)]()

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

TBD.
