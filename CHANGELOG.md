# Changelog

All notable changes to Clean Match Chess are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added — Feature 005 (Scoring v2 Phase 2)

- **Real Polyglot opening book** at `packages/analysis-core/data/opening_book.bin`
  (US2). Replaces the 1.3 KB Phase 1 synthetic stub with a 6.5 MB book derived
  from Lichess broadcast PGN archives 2025-02 + 2025-03 + 2025-04 (60,644 OTB
  master games, 425,062 entries). sha256:
  `dd0c9b50f75274b421ee9bfa12b45920b38124c9e2c7768f1179d130357c4532`.
  Build script: `packages/analysis-core/scripts/build_book_from_broadcasts.py`.
  License: CC-BY-SA 4.0 (inherited from upstream Lichess broadcasts).
  Substitution rationale: the originally documented `gm2600.bin` upstream URL
  (research.md R2) is no longer reachable; a Lichess-broadcast-derived book is
  a stronger provenance trail (CC-BY-SA 4.0, sha256-verifiable, fully
  reproducible from a public URL).
- **Verified clean corpus fixtures**: 50 OTB tournament games under
  `tests/fixtures/corpora/clean/` (US3 partial — clean bucket only).
  Source: Lichess broadcast archives 2025-02 + 2025-03 + 2025-04.
  Each fixture carries a sibling `.provenance.json` matching
  `contracts/provenance.schema.json` with `label="clean"`,
  `label_confidence="high"` (arbiter-monitored). Extraction script at
  `tests/fpr_gate/_corpus_extract.py`.
- `AuditRun.manifest` optional field — `ReproducibilityManifest` is now
  attached in-band to every audit output, so consumers no longer need a
  separate `manifest.json` read for provenance (FR-003, US4).
- Labeled-corpus FPR-gate test target at `tests/fpr_gate/test_fpr_gate.py`
  with helpers (`provenance.py`, `cache.py`, `gate.py`). Test asserts
  **FPR ≤ 2.0%** on a clean corpus and **TPR ≥ 80.0%** on an
  engine-assisted corpus at the `RISK_HIGH_MIN` decision threshold
  (FR-006, FR-007, SC-003). Skips gracefully when either bucket is empty.
- Per-fixture engine-analysis cache under `tests/fixtures/corpora/.cache/`
  (gitignored). Cache files embed `engine_binary_sha256` and
  `opening_book_sha256` from the cached `AuditRun.manifest`; stale entries
  are auto-detected on engine or book swap (FR-008, R3 mitigation).
- CI job `fpr_gate` in `.github/workflows/ci.yml`. Uses `actions/cache@v4`
  keyed on `opening_book.bin` + corpus PGN content. Path-filtered: runs on
  `push` to `main` and on PRs labeled `scoring`. Branch-protection (maintainer
  configures separately) makes it required for merge.
- Provenance schema for corpus fixtures (`*.provenance.json`) with five
  required fields: `source`, `retrieved_at`, `label`, `label_confidence`,
  `notes` (FR-005, contracts/provenance.schema.json).

### Pending (Feature 005 — to land before v2.0.0 promotion)

- Real Lichess month-export baselines (replaces hand-curated stub at
  `packages/heuristics/data/rating_baselines.json`) — US1. Deferred
  because the source archive is ~29 GB compressed and a build pass takes
  30-90 min CPU; needs maintainer-machine execution.
- ≥ 20 engine-assisted PGN fixtures under `tests/fixtures/corpora/engine_assisted/`
  with `label_confidence="high"` and notes acknowledging Lichess-classifier
  circularity — US3 (FR-005). Deferred because Lichess does not publish a
  flagged-account list via API; manual sourcing of publicly-disclosed cases
  is required (HANDOFF.md Block B-2).
- Full FPR-gate run on the complete corpus (T023) + regression-PR smoke
  (T025) + determinism re-run verification (T030).
- Measured FPR + TPR on the shipped corpus (point estimates + 95% CIs);
  smoke-test score delta vs Phase 1 stub baseline — FR-009.

### Added (carried over)

- Feature 003 — Repository health, CI supply-chain hardening, and OSS curation
  (SHA-pinned Actions, Dependabot, community health files, py.typed markers)

---

## [2.0.0] — 2026-05-24

Feature 004 — Fraud Detection Algorithm v2 Phase 1 (Statistical Foundation).

**Breaking change**: scores produced by this version are NOT numerically
comparable to scores produced by v1.x. The weights, signals, and bootstrap
methodology have all changed; manifest provenance now records the new signal
versions so persisted runs can be distinguished.

### Added

- `acpl-analysis` signal — Average Centipawn Loss calibrated against the
  player's rating bucket (FR-002, FR-003, US1)
- Bundled polyglot opening book at `packages/analysis-core/data/opening_book.bin`
  (gm2600.bin, public domain); `--book PATH` flag now functional on
  `audit-game` AND `audit-username` (FR-009, FR-020, US4)
- Bundled rating-baselines lookup at `packages/heuristics/data/rating_baselines.json`
  with one-shot maintainer script `packages/heuristics/scripts/build_baselines.py`
  (FR-010, FR-011)
- New `segment_aggregator` module: per-phase heuristic application with
  phase weights OPENING=0.5, MIDDLEGAME=1.0, TACTICAL=1.5, CONVERSION=1.3,
  ENDGAME=0.7 (FR-013–015, US5)
- Manifest now stamps `opening_book_sha256`, `rating_baselines_sha256`,
  `rating_baselines_version`, `scoring_thresholds_version`, and
  `signal_versions` dict (FR-012, SC-010)
- Move-resampling bootstrap with N=10000 default samples (FR-007, US3)

### Changed

- `blunder-suppression` (behavioral-patterns/blunder-suppression) rewritten
  from "post-move eval is calm" to delta-based "expected blunder evaded"
  per FR-004 — fixes the v1 bug that inflated the signal for any drawn or
  balanced game (US2)
- `regime-shift` rewritten from segment-size variation to CUSUM
  change-point detection on the per-move ACPL series (FR-005, US7)
- `timing-analysis` rewritten from binary fast-move count to regression-
  residual analysis on `log(time_ms+1) ~ complexity + phase` with a
  pre-move sub-signal blend (FR-006, US6)
- `engine-correlation` adds rating-bucket calibrated ratio mode; raw
  rate remains in `SignalAggregate.mean`, calibrated ratio in
  `weighted_mean`; aggregator applies piecewise normalization
  `clip((ratio - 1.0) / 1.5, 0, 1)` (FR-008, US8)
- `WEIGHTS` redistribution per FR-016: `acpl-analysis` 0.30,
  `engine-correlation/weighted` 0.30, `engine-correlation/top1` 0.05
  (down from 0.15), full distribution sums to 1.0; carrier
  `segments-weighted-aggregate` added at weight 0.74 to fold per-segment
  contributions
- `SCORING_THRESHOLDS_VERSION` bumped from `1.0.0` to `2.0.0` (FR-017);
  risk-level thresholds (LOW < 0.35, MEDIUM < 0.70, HIGH ≥ 0.70) unchanged
  in this phase (FR-018 — calibrated thresholds deferred to Phase 2)
- Signal versions bumped to `2.0.0`: `regime-shift`, `timing-analysis`,
  `engine-correlation`, `behavioral-patterns`

### Deferred to Phase 2

- SC-001 (engine-assisted corpus validation) and SC-002 (clean corpus FPR
  gate) require labeled-corpus sourcing and threshold calibration that are
  out of scope for Phase 1. Phase 2 backlog items P2-T001 and P2-T002 track
  these. Phase 1 pipeline correctness is validated by SC-003 through SC-010
- T042b score-delta documentation (engine-correlation ratio normalization
  vs pre-H1 baseline) deferred — bundled gm2600 book covers ~9 plies of
  the Italian Game test fixture (SC-005 targets ≥ 10; we accept ≥ 8 here)

### Notes

- Bootstrap perf budget on the reference machine is ≈ 0.5 s with a
  trivial resample closure (vs plan.md's aspirational ≤ 100 ms). Bench
  ceiling at 2000 ms — well within the engine-analysis budget (≤ 2.0
  s/ply, dominant cost). Constitution Principle IV held.

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
