# Implementation Plan: Fraud Detection Algorithm v2 — Phase 1 (Statistical Foundation)

**Branch**: `004-scoring-v2-phase1` | **Date**: 2026-05-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-scoring-v2-phase1/spec.md`

## Summary

Phase 1 of a multi-phase rework of the fraud-detection scoring engine.

**Primary requirement**: deliver an accurate, statistically defensible per-game suspicion score by (a) fixing two known algorithmic bugs (`blunder_suppression` and bootstrap CI), (b) introducing ACPL as a first-class signal with rating-bucket calibration, (c) wiring opening-book exclusion that was already scaffolded but never functional, (d) replacing the trivial timing heuristic with regression-residual analysis, (e) replacing the misnamed segment-size regime-shift with a CUSUM change-point detector over the ACPL series, and (f) propagating per-phase weights through the aggregation so engine-equivalent play in OPENING/ENDGAME counts less than the same in TACTICAL/CONVERSION.

**Technical approach**: pure internal refactor of `packages/heuristics/` and `packages/analysis-core/`. No new external dependencies beyond `numpy` (already transitively present via `python-chess`/`scipy` ecosystem; will be added explicitly to `packages/heuristics/pyproject.toml`). One bundled binary data file under 5 MB (a polyglot opening book) and one bundled JSON file (rating baselines, ~5 KB). All algorithms implementable in plain Python + numpy; no ML, no torch. Reproducibility preserved via deterministic seeds on the bootstrap RNG. Version bump `SCORING_THRESHOLDS_VERSION` 1.0.0 → 2.0.0 because score values shift discontinuously — CHANGELOG.md entry documents this.

## Technical Context

**Language/Version**: Python 3.12 (already pinned via root `.python-version`; constitution permits 3.11+).

**Primary Dependencies**: existing — `python-chess` (board + UCI + polyglot reader); `pydantic` v2 (dataclass schema enforcement). NEW — `numpy` ≥ 2.0 for vectorized regression/CUSUM math. NO new heavy deps (no torch, no scipy required — `numpy.polyfit` covers the OLS regression for timing).

**Storage**: read-only file inputs added — `packages/analysis-core/data/opening_book.bin` (polyglot binary, ≤ 5 MB) and `packages/heuristics/data/rating_baselines.json` (≤ 10 KB). Persisted output (AuditRun JSON) gains new fields under existing `Segment` entries; no schema-breaking removal.

**Testing**: `pytest` with hermetic fixtures. Existing test suites: `packages/heuristics/tests/`, `packages/analysis-core/tests/`, `apps/cli/tests/`. New test fixtures: at least 4 PGNs (engine-perfect-low-rated, engine-perfect-high-rated, regression-blunder-suppression, multi-segment phase distribution). Existing fixtures keep their pinned expected values; numeric fixtures are recomputed and re-pinned in the same PR with a per-test annotation explaining the v2 shift.

**Target Platform**: Linux (CI), macOS (developer). Pure Python; no platform-specific code paths.

**Project Type**: monorepo of Python packages (`packages/`) plus a CLI (`apps/cli`) and a Next.js frontend (`apps/frontend` — out of scope for this feature). Phase 1 touches only `packages/heuristics/`, `packages/analysis-core/`, `packages/shared-types/` (one minor field-typing tweak if needed), and possibly `apps/cli/src/cleanmatch_cli/main.py` if the `--book` flag wiring needs adjustment.

**Performance Goals** (per constitution Principle IV): bootstrap N=10000 with move-resampling MUST add ≤ 100 ms per game audit (measured on the reference machine — 8-core x86_64). Engine-correlation per-bucket lookup is O(1) per query → no impact on total game audit time. CUSUM on a 200-ply ACPL series runs in O(N) and adds ≤ 5 ms.

**Constraints**: must remain fully offline-capable after one-time data download (no runtime fetch from Lichess or any external service); audit must still produce reproducible bit-identical scores given the same PGN + engine + seed.

**Scale/Scope**: single audit run analyses 1 game (typical 40–200 plies) or up to 200 games for batch mode. All new code paths are linear in plies. No scale change vs current state.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| **I. Code Quality** | PASS | All new modules will be typed (`mypy --strict` clean), linted (`ruff`), and add no transitive bloat. `numpy` is the single new top-level dep; transitive impact reviewed before merge (numpy has no Python dependencies; pure C extension). |
| **II. Testing Standards (NON-NEGOTIABLE)** | PASS | Every new signal (acpl-analysis), every rewritten signal (blunder-suppression, regime-shift, timing-analysis), every aggregator change, and the rating-baselines lookup get dedicated unit tests with fixed PGN/FEN fixtures. Integration tests cover the end-to-end CLI flow on at least one known-clean + one known-suspect fixture. Coverage threshold remains ≥85% line, ≥80% branch on `src/`. |
| **III. UX Consistency** | PASS | No CLI flag changes (`--book` becomes functional but its surface was already declared). JSON export schema adds keys only, never removes. Exit codes unchanged. |
| **IV. Performance Requirements** | PASS w/ benchmark | Bootstrap N=10000 will be benchmarked on a 200-ply game: target ≤ 100 ms. CUSUM on 200-ply series: target ≤ 5 ms. Engine analysis time per ply (the dominant cost, 0.5–2.0 s) is unchanged because no engine-side change is made. A microbenchmark file `packages/heuristics/tests/bench_aggregator.py` is added to enforce the budget. |

**Constitution gate: PASS**. No violations; no Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/004-scoring-v2-phase1/
├── plan.md              # This file
├── research.md          # Phase 0: literature notes, polyglot book selection, numpy decision
├── data-model.md        # Phase 1: new dataclass additions, lookup-table schema, RatingBaseline shape
├── quickstart.md        # Phase 1: how to run an audit post-refactor + verify v2 score
├── contracts/
│   ├── rating_baselines.schema.json    # JSON schema for the bundled baselines table
│   ├── acpl_signal.contract.md         # Shape and semantics of the new acpl-analysis SignalAggregate
│   └── segment_score.contract.md       # Shape and semantics of Segment.signals + score_contribution
├── checklists/
│   └── requirements.md  # Spec quality checklist (already created during /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks command — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
clean-match-chess/
├── packages/
│   ├── shared-types/
│   │   └── src/shared_types/
│   │       ├── game.py                              # Move.eval_delta_cp ALREADY declared; verify type
│   │       └── signal.py                            # Segment.signals + score_contribution: ensure mutability for downstream population
│   │
│   ├── heuristics/
│   │   ├── data/
│   │   │   └── rating_baselines.json                # NEW — bundled rating-bucket lookup (US1 + US8)
│   │   ├── scripts/
│   │   │   └── build_baselines.py                   # NEW — maintainer-run one-shot generator (FR-011)
│   │   ├── src/heuristics/
│   │   │   ├── acpl_analysis/                       # NEW package (US1)
│   │   │   │   └── __init__.py                      #   acpl_signal() + helpers
│   │   │   ├── rating_baselines/                    # NEW package (US1 + US8)
│   │   │   │   └── __init__.py                      #   load_baselines(), bucket_for(rating)
│   │   │   ├── engine_correlation/__init__.py       # MODIFY — add ratio-vs-expected mode (US8)
│   │   │   ├── behavioral_patterns/__init__.py      # MODIFY — rewrite blunder_suppression (US2)
│   │   │   ├── regime_shift/__init__.py             # REWRITE — CUSUM on ACPL series (US7)
│   │   │   ├── timing_analysis/__init__.py          # REWRITE — regression residuals + premove (US6)
│   │   │   └── scoring/
│   │   │       ├── aggregator.py                    # MODIFY — new WEIGHTS dict; move-resample bootstrap (US3, FR-016)
│   │   │       ├── thresholds.py                    # MODIFY — bump SCORING_THRESHOLDS_VERSION to 2.0.0 (FR-017)
│   │   │       └── segment_aggregator.py            # NEW — phase-weighted segment aggregation (US5, FR-013–015)
│   │   └── tests/
│   │       ├── test_acpl_analysis.py                # NEW
│   │       ├── test_rating_baselines.py             # NEW
│   │       ├── test_blunder_suppression_v2.py       # NEW (incl. regression test vs old buggy output, SC-007)
│   │       ├── test_regime_shift_cusum.py           # NEW
│   │       ├── test_timing_regression.py            # NEW
│   │       ├── test_aggregator_bootstrap.py         # NEW (CI width comparisons, SC-004)
│   │       ├── test_segment_aggregator.py           # NEW (phase weight test, SC-006)
│   │       ├── test_engine_correlation_v2.py        # NEW (rating-bucket calibration, US8)
│   │       └── bench_aggregator.py                  # NEW — bootstrap perf budget (≤100 ms)
│   │
│   └── analysis-core/
│       ├── data/
│       │   └── opening_book.bin                     # NEW — bundled polyglot book ≤ 5 MB (US4, FR-009)
│       ├── src/analysis_core/
│       │   ├── engine/analysis.py                   # MINOR — eval_before bookkeeping for delta calc
│       │   └── pipeline/
│       │       ├── run.py                           # MODIFY — load book, compute eval_delta_cp, call segment aggregator
│       │       └── opening_book.py                  # NEW — thin wrapper around chess.polyglot.MemoryMappedReader
│       └── tests/
│           ├── test_opening_book.py                 # NEW
│           ├── test_run_acpl.py                     # NEW (end-to-end ACPL population)
│           └── test_run_phase_weights.py            # NEW (end-to-end per-phase application)
│
├── apps/cli/
│   └── src/cleanmatch_cli/main.py                   # VERIFY — --book flag actually plumbed (US4)
│
├── CHANGELOG.md                                     # MODIFY — v2.0.0 entry (FR-022)
└── specs/004-scoring-v2-phase1/                     # Spec dir (this feature)
```

**Structure Decision**: The repo already uses a monorepo of Python packages under `packages/` plus apps under `apps/`. Phase 1 follows that layout strictly. Two NEW packages are added inside `packages/heuristics/src/heuristics/` (`acpl_analysis/` and `rating_baselines/`) following the existing per-signal package convention. One NEW module is added inside `packages/analysis-core/src/analysis_core/pipeline/` (`opening_book.py`). One NEW module is added inside `packages/heuristics/src/heuristics/scoring/` (`segment_aggregator.py`) following the convention of the existing `aggregator.py`. No existing public API is removed; only additions and internal rewrites.

## Phase 0 — Research

Outputs to `specs/004-scoring-v2-phase1/research.md`:

1. **Polyglot opening book selection**. Comparison of public-domain polyglot books fit for ≤ 5 MB budget. Candidates: `Performance.bin` (Komodo/CCRL release, ~3.2 MB), `Cerebellum-Light.bin` (BrainFish, ~4.6 MB), `gm2600.bin` (older but widely cited, ~1.8 MB). **Recommendation**: gm2600.bin for v1 — smallest, well-attested in chess engine community, sufficient coverage of mainline theory for first 10–15 plies. Decision recorded with sha256, license note (public-domain), and source URL.

2. **Rating baseline derivation methodology**. How `build_baselines.py` derives the lookup table: download a single month of the Lichess open database (`https://database.lichess.org/standard/lichess_db_standard_rated_YYYY-MM.pgn.zst`); parse and bin by rating bucket; run a one-pass Stockfish analysis at depth 12 (cheap baseline) over 5000 randomly sampled games per bucket; compute the empirical distribution of (top-1 rate, weighted-top-1 rate, ACPL mean, ACPL stdev). Decision: this is a maintainer-run script; the COMMITTED JSON is the artifact, not the dataset; one-time runtime ~6 hours on the reference machine. The script must accept a `--seed` for reproducibility.

3. **Numpy choice for regression and CUSUM**. Decision: use `numpy.polyfit` for the timing regression (OLS, 2 features stacked); pure-Python CUSUM (no scipy needed) for the regime-shift detector. Justification: a single new top-level dep (numpy) versus pulling scipy adds ~30 MB of installed wheels and additional binary surface — not justified for two functions.

4. **Bootstrap implementation correctness**. Validation that the new move-resampling bootstrap correctly recomputes per-resample scores. Specifically: each resample picks N positions/moves with replacement from the original game's plies; for each resample, every heuristic is re-evaluated on the resampled set; the resulting score is one point in the empirical distribution. The 2.5/97.5 percentile gives the 95% CI. Edge case: if a resample is degenerate (e.g., all-book moves selected), the score for that resample is the configured "low data" default (0.0). Reproducibility: seed → identical bootstrap output.

5. **CUSUM parameter selection**. Decision: k=4σ default (4 standard deviations of running ACPL mean). Justification: at k=4, the expected false-positive rate on stationary Gaussian noise is below 1% per 1000 series (verified by Phase 0 simulation; documented in research.md with the simulation script). Higher k reduces power; lower k inflates false positives. k=4 chosen as a conservative default consistent with anti-cheating priorities (high precision over high recall on this signal).

## Phase 1 — Design & Contracts

Outputs:

1. **`data-model.md`** — concrete shapes:
   - `AcplSignal` extends `SignalAggregate` with extra fields `observed_acpl`, `expected_acpl_mean`, `expected_acpl_stdev`, `rating_bucket_label`. Score-normalized value [0,1] = `clamp((expected_mean - observed_acpl) / expected_stdev / 3.0, 0, 1)` — i.e., 1.0 when observed ACPL is 3σ below expected (very suspicious).
   - `RatingBaseline` schema: `{bucket_label: str, rating_low: int|None, rating_high: int|None, expected_top1: float, expected_weighted_top1: float, expected_acpl_mean: float, expected_acpl_stdev: float, sample_size: int}`. Seven entries: six rating buckets + `"rating-unknown"`.
   - `Segment.signals: tuple[SignalAggregate, ...]` already declared; just populated.
   - `Segment.score_contribution: float | None` already declared; populated as `phase_weight × segment_aggregate_score / sum_of_phase_weights`.

2. **`contracts/rating_baselines.schema.json`** — JSON schema for the bundled baselines file. Strict: `additionalProperties: false`, required keys enumerated, numeric ranges enforced.

3. **`contracts/acpl_signal.contract.md`** — semantics in plain English: when ACPL is computed, when it is silenced, how the score is derived, how the rating bucket is looked up.

4. **`contracts/segment_score.contract.md`** — semantics: which heuristics run per segment (engine-correlation, ACPL, blunder-suppression, timing-analysis), how the per-segment score is computed, how the phase weighting produces the game-level score.

5. **`quickstart.md`** — runnable steps:
   - `uv sync` (existing).
   - `cleanmatch audit-game tests/fixtures/regan_calibration_50.pgn --output json` (existing).
   - Inspect JSON: `dominant_signals` should now include `acpl-analysis`; CI width should be < 0.20 on long games; per-segment scores should differ from the game-level score.
   - Re-run with `--book /path/to/custom.bin` to verify custom book path works.
   - Run `pytest packages/heuristics packages/analysis-core` — all green.
   - Run `python packages/heuristics/tests/bench_aggregator.py` — perf budget held.

6. **Agent context update**: append a Phase 1 reference to `CLAUDE.md` between the `<!-- SPECKIT START -->` and `<!-- SPECKIT END -->` markers, pointing to `specs/004-scoring-v2-phase1/plan.md`.

## Phase 2 — Tasks (not produced here)

`/speckit-tasks` will translate Phase 0/1 outputs into `tasks.md`. Expected structure:

- **Phase 1 (Setup)**: declare numpy dep in `packages/heuristics/pyproject.toml`; download/verify polyglot book; place under `packages/analysis-core/data/`.
- **Phase 2 (Foundational, blocks all stories)**: populate `Move.eval_delta_cp` in `analysis-core/pipeline/run.py`; write `opening_book.py` wrapper; load book in `_analyse_positions`; write `rating_baselines/load.py`; commit `rating_baselines.json`.
- **Phase 3 (US1 — P1)**: `acpl_analysis/` package + signal computation + tests; register in WEIGHTS.
- **Phase 4 (US2 — P1)**: rewrite `blunder_suppression` using `eval_delta_cp`; regression test.
- **Phase 5 (US3 — P1)**: rewrite `aggregator.py` bootstrap to use move resampling; tests for CI width.
- **Phase 6 (US4 — P2)**: opening-book integration end-to-end test; wire `--book` flag in CLI.
- **Phase 7 (US5 — P2)**: `segment_aggregator.py` + per-segment heuristic dispatch; phase weights; end-to-end test.
- **Phase 8 (US6 — P2)**: rewrite `timing_anomaly` regression + premove; tests.
- **Phase 9 (US7 — P3)**: rewrite `regime_shift_score` CUSUM; tests.
- **Phase 10 (US8 — P3)**: rating-bucket calibration in `engine_correlation`; tests.
- **Phase 11 (Polish & cross-cutting)**: bump `SCORING_THRESHOLDS_VERSION` to 2.0.0; CHANGELOG entry; manifest version stamps; reproducibility verification; bench gate.

## Complexity Tracking

No constitution violations to justify. No 4th project. No new architectural patterns introduced beyond what the existing per-signal package convention already establishes. Numpy is a justified single new top-level dep (covered in research.md). Polyglot book is a small bundled binary (justified in research.md). Bootstrap N=10000 is a quality requirement, not extra complexity (justified by Principle II — defensibility of audit results).
