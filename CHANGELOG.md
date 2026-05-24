# Changelog

All notable changes to Clean Match Chess are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Feature 003 — Repository health, CI supply-chain hardening, and OSS curation
  (SHA-pinned Actions, Dependabot, community health files, py.typed markers)

---

## [1.0.0-design-system] — 2026-05-23

Forensic Analytics Design System — first stable release.

### Added

- `packages/design-system` v1.0.0: palette, typography, motion, and lexical
  design-token layers with full audit suite enforced in CI
- Four locked audits (`audit_palette`, `audit_typography`, `audit_motion`,
  `audit_lexical`) run as a required CI gate on every PR
- `design_system_audits` CI job (enforced, no `|| true`) as the quality gate
- Design system components catalogue (`docs/COMPONENTS.md`), lexicon
  (`docs/LEXICON.md`), and audit reference (`docs/AUDITS.md`)
- Forensic-appropriate color palette with WCAG AA contrast enforcement
- Motion spec with `prefers-reduced-motion` compliance gate
- Analytical lexicon with forbidden-terms loader and CI check

---

## [0.1.0] — 2026-05-23

MVP CLI auditor — Feature 001 complete (103/103 tasks).

### Added

- `cleanmatch` CLI with `audit-game`, `audit-username`, `show`, and `export`
  subcommands
- `packages/analysis-core`: PGN ingest, Stockfish engine pool, analysis pipeline
- `packages/heuristics`: five versioned signal modules — engine correlation,
  complexity analysis, tactical detection, regime shift, behavioral patterns
- `packages/report-engine`: HTML, PDF, and JSON report renderers
- `packages/shared-types`: Pydantic v2 schemas shared across all packages
- Reproducibility manifest (SHA256 of input PGN + Stockfish binary + heuristic
  versions) included in every report bundle
- 285 tests, 93% line coverage, enforced 85% gate
- `mypy --strict` and `ruff` clean on all packages
- Docker 2-stage build (`cleanmatch.Dockerfile`) for reproducible deployments
- Opening book support and known-clean / known-suspect PGN fixture suite
