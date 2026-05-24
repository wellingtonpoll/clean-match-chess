# analysis-core Changelog

## Unreleased (Feature 005 Phase 2)

### Added

- `packages/analysis-core/scripts/build_book_from_broadcasts.py` — one-shot
  maintainer script that builds a Polyglot opening book from a Lichess
  broadcast PGN archive (or any standard PGN file). Replaces the Phase 1
  synthetic stub generator.

### Changed

- `packages/analysis-core/data/opening_book.bin` — replaced Phase 1
  synthetic stub (1,296 bytes, 81 entries) with a real Lichess-broadcast-derived
  Polyglot book (6,800,992 bytes, 425,062 entries). Provenance, source archive
  sha256s, and reproduction recipe in `packages/analysis-core/data/README.md`.
- `_build_run` now attaches the `ReproducibilityManifest` to the returned
  `AuditRun.manifest` field (feature 005 FR-003 / US4). On-disk
  `manifest.json` continues to be written unchanged; consumers reading the
  audit JSON envelope no longer need a separate disk read for provenance.

## 2.0.0 — 2026-05-24 (Feature 004 Phase 1)

### Added

- `analysis_core.pipeline.opening_book.OpeningBook` — thin polyglot
  wrapper; bundled book at `packages/analysis-core/data/opening_book.bin`
  (gm2600.bin, public domain) loaded by default; `OpeningBook.empty()`
  sentinel for tests
- Pipeline auto-loads the book and stamps `Position.is_book=True` for
  positions covered by the book (FR-009, US4)
- `_populate_eval_deltas` fills `Move.eval_delta_cp` for every move
  using the side-to-move-relative convention (FR-001, US1)
- `run_single_game` / `run_username_batch` accept `book_path: str | None`
  kwarg (None → bundled book; `""` → empty sentinel; `<path>` → custom
  polyglot file) (FR-019, T028)
- Manifest stamping: `opening_book_sha256`, `rating_baselines_sha256`,
  `rating_baselines_version`, `scoring_thresholds_version`, and
  `signal_versions` are now persisted on every audit's
  `ReproducibilityManifest` (FR-012, SC-010)
- Pipeline invokes the new `segment_aggregator.aggregate_segments` to
  produce phase-weighted per-segment scoring; the segment-weighted
  aggregate flows into `aggregate_score` as a synthetic
  `segments-weighted-aggregate` signal (FR-013–015, US5)
- Pipeline wires `subject_rating` (parsed from PGN headers) and
  `baselines` into engine-correlation calls for rating-bucket calibration
  (FR-008, US8)

### Changed

- `regime_shift_score` invocation now takes `(positions, moves)` instead
  of `(segments,)` — segments-based fallback returns silenced aggregate
- `blunder_suppression` invocation passes `moves` as new positional arg
- Per-signal version strings bumped in `SIGNAL_VERSIONS`: regime-shift
  2.0.0, timing-analysis 2.0.0, behavioral-patterns 2.0.0
