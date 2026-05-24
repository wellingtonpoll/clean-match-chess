---
description: "Task list for feature 004 — Fraud Detection Algorithm v2 (Phase 1)"
---

# Tasks: Fraud Detection Algorithm v2 — Phase 1 (Statistical Foundation)

**Input**: Design documents from `/specs/004-scoring-v2-phase1/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: REQUIRED — constitution Principle II (Testing Standards is NON-NEGOTIABLE). Every signal, scoring change, and rendering path MUST have unit tests with fixed PGN/FEN fixtures. Tests are listed before their corresponding implementation tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Includes exact file paths in descriptions

## Path Conventions

Monorepo of Python packages under `packages/` plus apps under `apps/`. Paths below are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add numpy dependency, scaffold new data dirs, prepare bundled artifacts.

- [X] T001 Add `numpy >= 2.0` to `packages/heuristics/pyproject.toml` `[project.dependencies]` and run `uv sync` from repo root to update the lockfile.
- [X] T002 Create directories: `packages/heuristics/data/`, `packages/heuristics/scripts/`, `packages/analysis-core/data/`. Add `.gitkeep` files so empty dirs are committed before binary artifacts land. T003 and T007 must `rm` the corresponding `.gitkeep` when they add the real artifact (otherwise leftover `.gitkeep` lingers as orphan).
- [X] T003 [P] Download `gm2600.bin` polyglot opening book (per research.md R1) and commit at `packages/analysis-core/data/opening_book.bin`. Verify sha256 against the upstream source URL and record it in a `packages/analysis-core/data/README.md` (1-line provenance + sha256). Also `rm packages/analysis-core/data/.gitkeep`.
- [X] T004 [P] Write `packages/heuristics/scripts/build_baselines.py` per research.md R2 (one-shot maintainer script: download Lichess month-export, sample, compute per-bucket stats, emit JSON conforming to `contracts/rating_baselines.schema.json`). Include a `--dry-run` mode for code review without downloading the multi-GB dataset.
- [X] T004b [P, lifted from Phase 11 — M-NEW1] Commit canonical smoke-test fixture. Action: locate any valid 40+ ply PGN with WhiteElo and BlackElo headers (recommend a public-domain Lichess game via `https://lichess.org/api/game/export/{id}`); copy to `tests/fixtures/audit_v2_smoke.pgn`. Requirements: ≥ 40 half-moves, both Elo headers present, legal game termination, no chat or annotations. Canonical fixture for T042b (Phase 10) and T048 (Phase 11) — must exist before those tasks execute.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Populate `Move.eval_delta_cp`, load opening book, load rating baselines. These three deliverables block every user story.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Create `packages/analysis-core/src/analysis_core/pipeline/opening_book.py` — thin wrapper around `chess.polyglot.MemoryMappedReader`. Public API: `OpeningBook.load(path)`, `OpeningBook.contains(board) -> bool` (returns True iff the book has any entry with `weight > 0`), `OpeningBook.sha256() -> str`, `OpeningBook.default_path() -> Path`. Module-level singleton accessor.
- [X] T006 [P, depends on T007] Create `packages/heuristics/src/heuristics/rating_baselines/__init__.py` — expose `RatingBaselines` singleton. Public API: `get_baselines().bucket_for(rating: int | None) -> RatingBaseline`, `get_baselines().for_label(label: str) -> RatingBaseline`. **Lazy-load** the `data/rating_baselines.json` on first call (NOT at module import) so test discovery before T007 produces the JSON does not raise ImportError. Validate against schema at first load; raise on schema mismatch. Recommended pattern:

  ```python
  _BASELINES: RatingBaselines | None = None
  def get_baselines() -> RatingBaselines:
      global _BASELINES
      if _BASELINES is None:
          _BASELINES = _load_and_validate(BASELINES_PATH)
      return _BASELINES
  ```
- [X] T007 [P] Run `packages/heuristics/scripts/build_baselines.py` (T004) ONCE in maintainer environment to produce `packages/heuristics/data/rating_baselines.json`. Commit the JSON. Also `rm packages/heuristics/data/.gitkeep`. If the dataset is unavailable at task-execution time, commit a hand-curated stub JSON conforming to the schema with documented placeholder values and a TODO note in research.md — defer the real data refresh to a follow-up. (Acceptable per research.md: the artifact is the truth; the script is reproducibility infrastructure.)
- [X] T008 Modify `packages/analysis-core/src/analysis_core/pipeline/run.py`: in `_analyse_positions`, load the opening book singleton (default path from T005); for each position, set `Position.is_book = True` when `book.contains(board)`. Add a `book: OpeningBook | None = None` optional parameter to `_analyse_positions` so tests can inject a custom book or disable.
- [X] T009 Modify `packages/analysis-core/src/analysis_core/pipeline/run.py`: in `_build_run` (or per-move loop), compute `Move.eval_delta_cp` for every move using the previous and current position's `eval_cp` per FR-001 (side-to-move perspective: positive delta means the played move improved the player's position). Handle None evaluations gracefully (delta becomes None when either side is None).
- [X] T010 [P] Modify `packages/analysis-core/src/analysis_core/pipeline/run.py`: thread the `opening_book_sha256` and `rating_baselines_sha256` into the existing manifest builder so they appear in `AuditRun.manifest`. Stamp `signal_versions` dict with the per-signal version strings.  *(Partial: opening_book_sha256 flows through existing `build_manifest`; rating_baselines_sha256 and signal_versions are computed but not yet persisted because `ReproducibilityManifest` is `frozen + extra="forbid"` and shared-types schema changes are out of scope per constitution constraint. Follow-up: extend ReproducibilityManifest schema in a separate change.)*
- [X] T011 Add unit test `packages/analysis-core/tests/test_opening_book.py` — verifies `OpeningBook.contains()` on a known Italian Game position returns True, on a random middlegame returns False, sha256 is stable across loads.
- [X] T012 Add unit test `packages/analysis-core/tests/test_run_eval_delta.py` — given a 6-ply hand-crafted PGN, the pipeline output has `eval_delta_cp` populated on every move with the expected sign and magnitude (use a static analyzer with pinned eval values for hermetic determinism).
- [X] T013 Add unit test `packages/heuristics/tests/test_rating_baselines.py` — `bucket_for(1500)` returns `"1201-1500"` (or `"1501-1800"` per the boundary convention in data-model.md), `bucket_for(None)` returns `"rating-unknown"`, `bucket_for(99999)` falls back to `"rating-unknown"`, schema validates.

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - ACPL Computation and Distribution Signal (Priority: P1) 🎯 MVP

**Goal**: Emit the `acpl-analysis` heuristic signal calibrated against player rating bucket; populate the `Move.eval_delta_cp` field that downstream stories depend on.

**Independent Test**: Per spec — audit two PGNs with engine-perfect quality (ACPL≈10), one with rating header 1500, one with 2700. The 1500 audit must score ≥ 0.65; the 2700 audit must score ≤ 0.45.

### Tests for User Story 1

- [X] T014 [P] [US1] Write `packages/heuristics/tests/test_acpl_analysis.py` — covers the contract in `contracts/acpl_signal.contract.md`: (a) acpl_signal returns a SignalAggregate; (b) silencing when samples < 10; (c) silencing on all-book input; (d) suspicion value formula z-scaling correctness; (e) rating-unknown bucket fallback; (f) US1 AS1 (1500 + ACPL=10 → suspicion ≥ 0.65); (g) US1 AS2 (2700 + ACPL=10 → suspicion ≤ 0.45). Use the `RatingBaselines` from T007 (or a stub fixture if the real artifact is unavailable).

### Implementation for User Story 1

- [X] T015 [P] [US1] Create `packages/heuristics/src/heuristics/acpl_analysis/__init__.py` per `contracts/acpl_signal.contract.md`. Public API: `acpl_signal(positions, moves, subject_color, subject_rating, baselines) -> SignalAggregate`. Internal helpers compute observed mean/stdev, look up bucket, derive suspicion. Module exposes `signal_version()` returning a `HeuristicVersion`.
- [X] T016 [US1] Modify `packages/heuristics/src/heuristics/scoring/aggregator.py` `WEIGHTS` dict per FR-016: add `"acpl-analysis": 0.30`, reduce `"engine-correlation/top1"` from 0.15 to 0.05, and redistribute the remaining weights to match FR-016 exactly. Update any docstring or comment referencing the old weights.
- [X] T017 [US1] Modify `packages/analysis-core/src/analysis_core/pipeline/run.py` `_build_run` to extract the subject's rating from PGN headers (WhiteElo for white subject, BlackElo for black; coerce to int; clamp to plausible range; None if missing), invoke `acpl_signal()` with this rating, and include the resulting `SignalAggregate` in the list passed to `aggregate_score`.
- [X] T018 [US1] Add integration test `packages/analysis-core/tests/test_run_acpl_integration.py` — uses a static analyzer fixture to verify the end-to-end pipeline emits an `acpl-analysis` signal in `dominant_signals` for a high-ACPL-suspicion synthetic input, and emits a low value for a normal input.

**Checkpoint**: At this point, US1 is fully functional and testable independently.

---

## Phase 4: User Story 2 - Blunder-Suppression Bug Fix (Priority: P1)

**Goal**: Rewrite `blunder_suppression` to use `eval_delta_cp` (now populated by T009) and the correct delta-based semantics per FR-004.

**Independent Test**: Run the curated regression-test PGN; the new implementation returns 0.0 where the old returned non-zero, and 1.0 in the genuine-evasion case.

### Tests for User Story 2

- [ ] T019 [P] [US2] Write `packages/heuristics/tests/test_blunder_suppression_v2.py` — covers US2 AS1/AS2/AS3: (a) a hand-crafted position where complexity > 0.6 and `top_moves[1]` has eval_delta_cp ≤ -200 and the played move has eval_delta_cp > -100 → counts as evaded → signal value 1.0; (b) a synthetic game with zero qualifying positions → samples=0, silenced; (c) the regression fixture where the OLD implementation produced a non-zero misleading value and the NEW one produces 0.0 — assert the values differ and the new one is correct per the contract.

### Implementation for User Story 2

- [ ] T020 [US2] Modify `packages/heuristics/src/heuristics/behavioral_patterns/__init__.py::blunder_suppression()` per FR-004. New signature should accept `moves` in addition to `positions` (the existing function only takes positions; this is an API addition, not a break, since the only caller is `pipeline/run.py`). Bump `__signal_version__` from `"0.1.0"` to `"2.0.0"` to reflect the breaking semantic change.
- [ ] T021 [US2] Modify `packages/analysis-core/src/analysis_core/pipeline/run.py` `_build_run` to pass `moves` into `blunder_suppression(positions, moves)`. Update the line where the function is invoked.

**Checkpoint**: US2 fully functional; new and old behaviour distinguishable in regression test.

---

## Phase 5: User Story 3 - Bootstrap Confidence Interval Statistical Correctness (Priority: P1)

**Goal**: Replace the 8-contribution bootstrap with a move-resampling bootstrap per FR-007. CI width drops on long games.

**Independent Test**: 120-ply game has CI width ≤ 0.20; 25-ply game has CI width ≥ 1.5× the 120-ply width for similar signals.

### Tests for User Story 3

- [ ] T022 [P] [US3] Write `packages/heuristics/tests/test_aggregator_bootstrap.py` — covers US3 AS1/AS2/AS3: (a) synthetic 120-ply input produces CI width ≤ 0.20; (b) synthetic 25-ply input with similar signal means produces CI width ≥ 1.5× the 120-ply case; (c) two runs with the same seed produce bit-identical CIs; (d) degenerate input (5 moves) returns CI = (0.0, 1.0).

### Implementation for User Story 3

- [ ] T023 [US3] Modify `packages/heuristics/src/heuristics/scoring/aggregator.py`: rewrite `aggregate_score()` and `_bootstrap_ci()` per FR-007 + research.md R4. New signature: `aggregate_score(signals, *, positions=None, moves=None, bootstrap_samples=10000, seed=0)`. When `positions` and `moves` are provided, run the move-resampling bootstrap: per resample, pick N plies with replacement, recompute every heuristic on the resampled subset, then aggregate. Compute 2.5/97.5 percentiles. When `positions`/`moves` are NOT provided, fall back to legacy contribution-bootstrap (for callers that haven't migrated yet — but emit a `DeprecationWarning`). Bump `BOOTSTRAP_SAMPLES_DEFAULT` to 10000.
- [ ] T024 [US3] Modify `packages/analysis-core/src/analysis_core/pipeline/run.py` `_build_run` to pass `positions` and `moves` into `aggregate_score()`. Confirm no caller still uses the legacy path; the DeprecationWarning should never trigger in normal repo usage.
- [ ] T025 [US3] Add benchmark `packages/heuristics/tests/bench_aggregator.py` — measures aggregate_score() with 10000 bootstrap samples on a 200-ply synthetic game; asserts wall time ≤ 100 ms. Use `pytest-benchmark` if already a dep; otherwise plain `time.perf_counter()`.

**Checkpoint**: US3 functional; CI semantics now statistically meaningful.

---

## Phase 6: User Story 4 - Opening Book Integration (Priority: P2)

**Goal**: Make the bundled opening book actually exclude book positions from the suspicion denominator end-to-end; expose `--book` flag in CLI.

**Independent Test**: Italian Game 60-ply PGN: with book on, engine-correlation uses 46 ply samples; with book off, 60.

### Tests for User Story 4

- [ ] T026 [P] [US4] Write `packages/analysis-core/tests/test_run_book_exclusion.py` — covers US4 AS1/AS3: feed the same Italian Game PGN through the pipeline twice (once with the bundled book loaded, once with an empty stub book) and assert the engine-correlation signal `samples` count differs by at least 10. Also assert `is_book == True` on the first ~12 plies under the bundled book.

### Implementation for User Story 4

- [ ] T027 [US4] Modify `apps/cli/src/cleanmatch_cli/main.py`. `audit_game` already declares `--book`; add the same `--book <PATH>` optional argument to `audit_username` (per FR-020 amendment — explicit flag addition, not a violation). Thread `book` value through to `run_single_game` and `run_username_batch`. When the flag is None, use `OpeningBook.default_path()`. Help text: `"--book PATH: path to Polyglot .bin file; overrides bundled default."` Acceptance: `cleanmatch audit-username --book /tmp/custom.bin USER` runs without error; `cleanmatch audit-username USER` (no flag) uses bundled default.
- [ ] T028 [US4] Modify `packages/analysis-core/src/analysis_core/pipeline/run.py` `run_single_game` and `run_username_batch`: accept a `book_path: str | None = None` keyword arg. Pass through to `_analyse_positions`. When `book_path` is None, default to `OpeningBook.default_path()`. When `""` (explicit empty), pass a no-op book (no positions marked as book). Document the convention in the docstring.

**Checkpoint**: US4 functional; book exclusion active by default.

---

## Phase 7: User Story 5 - Per-Segment Heuristic Application (Priority: P2)

**Goal**: Apply heuristics per segment; aggregate with phase weights per FR-013–015 + `contracts/segment_score.contract.md`.

**Independent Test**: Two synthetic AuditRun fixtures with identical aggregate engine-correlation but signals concentrated in TACTICAL vs ENDGAME. TACTICAL-concentrated scores ≥ 30% higher.

### Tests for User Story 5

- [ ] T029 [P] [US5] Write `packages/heuristics/tests/test_segment_aggregator.py` — covers US5 AS2/AS3 + SC-006: synthetic segments with identical signal values but different phase distributions; TACTICAL-concentrated game scores ≥ 30% higher than ENDGAME-concentrated; the sum of segment `score_contribution` equals the game score within 1e-9.

### Implementation for User Story 5

- [ ] T030 [US5] Create `packages/heuristics/src/heuristics/scoring/segment_aggregator.py` per `contracts/segment_score.contract.md`. Public API: `aggregate_segments(segments, positions, moves, baselines, subject_rating, subject_color) -> tuple[float, tuple[Segment, ...]]` — returns the game-level segment-weighted score AND the segments mutated with populated `signals` and `score_contribution`. Internally: for each segment, slice positions/moves by `segment.ply_range`, run per-segment heuristics (engine-correlation, acpl-analysis, blunder-suppression, timing-analysis when applicable), compute raw aggregate, then phase-weight and accumulate.
- [ ] T031 [US5] Modify `packages/analysis-core/src/analysis_core/pipeline/run.py` `_build_run`: replace the current "run all heuristics on full game" flow with: (a) compute segments via existing `segment_game()`; (b) call `aggregate_segments()` to get the segment-weighted score and populated Segment objects; (c) compute game-level-only heuristics (regime-shift, precision-burst, complexity, tactical-detection, engine-correlation/top3) on the full positions/moves; (d) call `aggregate_score()` with the union of the segment-weighted score (as a synthetic SignalAggregate) and the game-level-only signals. Persisted `AuditRun.segments` now contains populated Segment objects.
- [X] T032 [US5, RESOLVED — no action] `Segment` dataclass in `packages/shared-types/src/shared_types/signal.py` is `frozen=False` (default Python behavior); `signals: tuple[SignalAggregate, ...]` and `score_contribution: float | None` are assignable post-construction. No modification needed. If a future refactor adds `frozen=True`, switch to the `dataclasses.replace()` pattern documented in T030. This task is closed.
- [ ] T033 [US5] Add unit test `packages/heuristics/tests/test_segment_phase_weights.py` — asserts the exact phase weights are OPENING=0.5, MIDDLEGAME=1.0, TACTICAL=1.5, CONVERSION=1.3, ENDGAME=0.7 (no drift); the constants are exported from the module so consumers/manifests can reference them.

**Checkpoint**: US5 functional; per-segment signals visible in JSON export.

---

## Phase 8: User Story 6 - Timing Regression Signal (Priority: P2)

**Goal**: Replace binary fast-move count with regression-residual analysis + pre-move sub-signal per FR-006 + US6 contract.

**Independent Test**: Synthetic game with slow-easy + fast-hard plays detects > 70% of hard-position moves as anomalies.

### Tests for User Story 6

- [ ] T034 [P] [US6] Write `packages/heuristics/tests/test_timing_regression.py` — covers US6 AS1/AS2/AS3: (a) regression fit on synthetic 30-move input produces expected residual signs; (b) pre-move sub-signal computes fraction of `time_spent_ms < 300` on non-trivial complexity; (c) combination weight 0.7 × residuals + 0.3 × premove; (d) no timing data → silenced; (e) per US6 independent test, slow-easy/fast-hard synthetic input flags > 70% of hard-position moves.

### Implementation for User Story 6

- [ ] T035 [US6] Rewrite `packages/heuristics/src/heuristics/timing_analysis/__init__.py::timing_anomaly()` per FR-006 + research.md R3. Use **`numpy.linalg.lstsq`** (NOT `polyfit`, which is 1-D only) on stacked features (complexity composite, phase ordinal per FR-006). Reference implementation:

  ```python
  import numpy as np

  X = np.column_stack([complexity_scores, phase_ordinals])
  X_aug = np.column_stack([X, np.ones(len(X))])  # bias term
  coeffs, _, _, _ = np.linalg.lstsq(X_aug, log_times, rcond=None)
  # coeffs = [beta_complexity, beta_phase, intercept]
  predicted = X_aug @ coeffs
  residuals = log_times - predicted
  ```

  Compute residual stdev; signal value = fraction of moves with `|residual| > 2 × stdev`. Combine with pre-move rate per US6 AS2 (final = 0.7 × residual_rate + 0.3 × premove_rate). Bump `__signal_version__` from `"0.1.0"` to `"2.0.0"`.
- [ ] T036 [US6] Confirm `packages/analysis-core/src/analysis_core/pipeline/run.py` continues to pass the right inputs to the new `timing_anomaly()` (signature unchanged). Update the segment_aggregator (T030) to optionally invoke timing per segment when ≥ 50% of segment moves have timing data.

**Checkpoint**: US6 functional.

---

## Phase 9: User Story 7 - Regime-Shift via CUSUM Change-Point Detection (Priority: P3)

**Goal**: Replace segment-size variation with CUSUM on per-move ACPL series per FR-005 + research.md R5.

**Independent Test**: Synthetic ACPL series with engineered change point at index 5 → detector returns a change point in [4..7]; flat series → zero.

### Tests for User Story 7

- [ ] T037 [P] [US7] Write `packages/heuristics/tests/test_regime_shift_cusum.py` — covers US7 AS1/AS2/AS3: (a) synthetic ACPL series with a true change point → CUSUM k=4 detects in expected range; (b) **1000 stationary noise series generated with `numpy.random.default_rng(seed=42)`** (e.g., `[rng.normal(0, 1, size=200) for _ in range(1000)]`) → false-positive rate ≤ **1.5%** (0.5% cushion above the 1.0% target to prevent flakiness from BLAS/LAPACK float drift across platforms — constitution Principle II prohibits flaky tests); (c) game < 10 non-book plies → 0.0 with 0-sample aggregate; (d) monotonically improving series does NOT trigger (per edge case).

### Implementation for User Story 7

- [ ] T038 [US7] Rewrite `packages/heuristics/src/heuristics/regime_shift/__init__.py::regime_shift_score()` per FR-005 + research.md R5. New signature: `regime_shift_score(positions, moves, k_sigma=4.0) -> SignalAggregate`. Compute ACPL series from `move.eval_delta_cp` over non-book plies; apply CUSUM with `k = k_sigma * running_sigma`; count change points; normalize signal to [0,1] via `min(1.0, count / 3.0)`. Bump `__signal_version__` to `"2.0.0"`.
- [ ] T039 [US7] Confirm `packages/analysis-core/src/analysis_core/pipeline/run.py` invokes `regime_shift_score(positions, moves)` with updated args. Update segment_aggregator to NOT call regime-shift per-segment (it's a game-level-only signal per `contracts/segment_score.contract.md`).

**Checkpoint**: US7 functional.

---

## Phase 10: User Story 8 - Rating-Bucket Calibration of Engine-Correlation (Priority: P3)

**Goal**: Compute engine-correlation match rates as ratios vs rating-bucket-expected rates per FR-008.

**Independent Test**: 2700 player with 75% top-1 → ratio ≈ 1.0; 1200 player with 75% top-1 → ratio ≥ 2.5.

### Tests for User Story 8

- [ ] T040 [P] [US8] Write `packages/heuristics/tests/test_engine_correlation_v2.py` — covers US8 AS1/AS2/AS3: (a) ratio = observed / expected for top-1 and weighted top-1; (b) all 6 rating buckets + rating-unknown queryable; (c) missing rating → rating-unknown bucket used; (d) US8 independent test (1200 vs 2700 with same 75% top-1 → ratios differ by ≥ 1.5).

### Implementation for User Story 8

- [ ] T041 [US8] Modify `packages/heuristics/src/heuristics/engine_correlation/__init__.py::engine_correlation()`. Add `subject_rating: int | None` and `baselines: RatingBaselines` parameters. Compute the existing observed rates AND the ratios `observed / expected` for top-1, weighted-top-1, AND top-3. Store the ratio in `SignalAggregate.weighted_mean` (interpretation: 1.0 = matches expectation; >1.0 = exceeds). Keep `SignalAggregate.mean` as the raw observed rate for backward compatibility with downstream consumers. If the rating bucket lookup does not include `expected_top3`, emit the top-3 SignalAggregate with `samples=0` (silenced; aggregator excludes silenced signals from weighted mean). Bump `__signal_version__` to `"2.0.0"`.
- [ ] T042 [US8] Modify `packages/analysis-core/src/analysis_core/pipeline/run.py` `_build_run`: thread `subject_rating` and `baselines` into `engine_correlation()`. Update segment_aggregator (T030) similarly.
- [ ] T042b [US8, BEFORE T043 implementation lands] Capture pre-H1-change baseline scores for delta documentation. Run on the test corpus before applying the piecewise normalization in T043:

  ```bash
  cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/baseline_pre_H1.json
  # also audit greg589's last 3 games if available
  ```

  After T043 lands, repeat → `/tmp/baseline_post_H1.json`. Diff the `.score.score` values. Document representative deltas in the CHANGELOG v2.0.0 entry (T045): e.g. "Engine-correlation ratio normalization changed (H1). Sample deltas: greg589/game1: 0.464 → X.XXX (Δ +/-Y)". This is documentation work, not a gate — but maintainers need the numbers to explain v1→v2 score shifts to existing users.
- [ ] T043 [US8] Modify `packages/heuristics/src/heuristics/scoring/aggregator.py`: when consuming engine-correlation signals, prefer `weighted_mean` (the new ratio) for the scoring contribution. Apply piecewise linear normalization centered at baseline (per FR-008 §Mapping + `contracts/segment_score.contract.md` §Normalization):

  ```python
  import numpy as np
  def ratio_to_score(ratio: float) -> float:
      return float(np.clip((ratio - 1.0) / 1.5, 0.0, 1.0))
  ```

  - ratio 1.0 → score 0.0 (matches baseline; no suspicion contribution)
  - ratio 2.5 → score 1.0 (maximum suspicion)
  - ratio < 1.0 → score 0.0 (clamped; below-expectation play not penalized)

  Applies to top-1, weighted-top-1, top-3 ratios identically. Update tests for `aggregator` accordingly.

**Checkpoint**: All 8 user stories complete.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Version bumps, CHANGELOG, end-to-end determinism check, quickstart validation.

- [ ] T044 Modify `packages/heuristics/src/heuristics/scoring/thresholds.py::SCORING_THRESHOLDS_VERSION` from `"1.0.0"` to `"2.0.0"` per FR-017.
- [ ] T045 [P] Modify `CHANGELOG.md` at repo root: add a `## [2.0.0] — 2026-05-24` entry per FR-022 + SC-009. Explicitly state: scores from runs ≤ v1.x are NOT comparable; new `acpl-analysis` signal added; `blunder-suppression` bug fix; bootstrap methodology changed; bundled opening book + rating baselines included; signal versions bumped (regime-shift 2.0.0, timing-analysis 2.0.0, engine-correlation 2.0.0). Include the H1 sample deltas captured by T042b (e.g. "greg589/game1: 0.464 → X.XXX"). **Phase 1 scope note**: "Phase 1 ships the scoring pipeline + signal correctness. Empirical false-positive-rate validation against labeled corpora is deferred to Phase 2 (see deferred SC-001, SC-002)."
- [ ] T046 [P] Modify `packages/heuristics/CHANGELOG.md`: per-signal bump entries with brief rationale per signal.
- [ ] T047 [P] Modify `packages/analysis-core/CHANGELOG.md`: book integration + manifest stamping entries.
- [ ] T048 [depends on T004b] Add end-to-end test `apps/cli/tests/test_audit_game_v2.py` — run `cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn`, assert: (a) `manifest.scoring_thresholds_version == "2.0.0"`; (b) `manifest.opening_book_sha256` is non-zero; (c) `manifest.rating_baselines_version` is non-zero; (d) `dominant_signals` contains `acpl-analysis` if the game is non-trivial; (e) all `Move.eval_delta_cp` are populated; (f) all `Segment.signals` and `score_contribution` are populated. File path is fixed — do not accept "whichever exists".
- [ ] T049 Add determinism test `packages/heuristics/tests/test_determinism_v2.py` — run `aggregate_score()` twice on identical inputs with `seed=0`; bit-identical CI and dominant_signals.
- [ ] T050 [P] Run `uv run ruff check .` from repo root; fix any new violations introduced by Phase 1.
- [ ] T051 [P] Run `uv run mypy --strict packages/heuristics/src packages/analysis-core/src`; fix any type errors introduced. No new `# type: ignore` without inline justification (constitution Principle I).
- [ ] T052 Run `uv run pytest --cov=packages --cov-report=term --cov-fail-under=85`; confirm coverage holds at ≥ 85% line / ≥ 80% branch on the new modules.
- [ ] T053 Execute `quickstart.md` step-by-step manually; confirm every numbered step produces the expected output. Document any deviation in a follow-up issue.
- [ ] T054 Final review against constitution: Principle I (code quality + no bloat), Principle II (tests for every new signal — confirm coverage), Principle III (no CLI flag changes), Principle IV (bench passes ≤ 100 ms). Sign off in PR description.

---

## Dependencies & Execution Order

### Coverage notes

- **SC-001 and SC-002 are demoted to Phase 2** (H3 resolution). No corpus tasks required in Phase 1. Phase 2 backlog items track the deferred validation: P2-T001 (engine-assisted corpus), P2-T002 (clean corpus + FPR gate). Do NOT create `tests/fixtures/corpora/` in this phase.

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **T003 and T004** are marked `[P]` (parallel) but both depend on **T002** (directory creation) completing first. T002 is sequential; T003/T004 cannot start until T002 exits.
- **T004b** lifted from Phase 11 (was T047b) — fixture must exist before T042b (Phase 10 H1 baseline capture) and T048 (Phase 11 end-to-end test). T004b has no real deps (just a file commit) so belongs in Setup.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories.
- **User Story phases (3 → 10)**: All depend on Foundational. Within the P1 group (US1, US2, US3), US2 and US3 also depend on US1 (they consume `Move.eval_delta_cp` populated by US1).
- **Polish (Phase 11)**: Depends on all stories selected for this PR being complete.

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 (foundational). Required for US2, US3, US7, US8 (they all consume eval_delta_cp or baselines).
- **US2 (P1)**: Depends on US1 (uses eval_delta_cp). Independently testable post-US1.
- **US3 (P1)**: Depends on US1 (move-resample bootstrap recomputes signals including ACPL). Independently testable.
- **US4 (P2)**: Depends on Phase 2 (book loaded). Independently testable.
- **US5 (P2)**: Depends on US1 (per-segment ACPL needs eval_delta_cp). Independently testable post-US1.
- **US6 (P2)**: Depends on Phase 2 (no eval_delta_cp needed for timing). Independently testable.
- **US7 (P3)**: Depends on US1 (CUSUM on ACPL series). Independently testable post-US1.
- **US8 (P3)**: Depends on Phase 2 (baselines loaded). Independently testable.

### Within Each User Story

- Tests MUST be written and FAIL before implementation tasks (red → green → refactor per constitution Principle II).
- For US5: `segment_aggregator.py` (T030) before pipeline integration (T031).
- For US7/US8: heuristic modification (T038/T041) before pipeline integration (T039/T042).

### Parallel Opportunities

- **Within Phase 1**: T003 (book download) and T004 (script write) parallel.
- **Within Phase 2**: T006 (baselines module) and T007 (run script) parallel after T005. T010 (manifest) parallel with T011 (book test) and T013 (baselines test).
- **Across user stories**: After Phase 2, US1 must finish first (block on US2/US3/US5/US7), but US4 and US6 can start in parallel with US1.
- **Tests within a story**: All test-writing tasks marked [P] within a phase can run in parallel.

---

## Parallel Example: User Story 1 + User Story 4 simultaneous

```bash
# After Phase 2 completes, kick off US1 (P1, MVP path) and US4 (P2, independent of US1) together:

# Developer A — US1:
Task: T014 [US1] Write test_acpl_analysis.py
Task: T015 [US1] Create heuristics/acpl_analysis/__init__.py

# Developer B — US4:
Task: T026 [US4] Write test_run_book_exclusion.py
Task: T027 [US4] Wire --book flag in CLI
```

---

## Implementation Strategy

### MVP First (US1, US2, US3 — all P1)

1. Complete Phase 1 (Setup).
2. Complete Phase 2 (Foundational) — CRITICAL gate.
3. Complete Phase 3 (US1) — ACPL signal active; eval_delta_cp populated.
4. Complete Phase 4 (US2) — blunder-suppression bug fixed.
5. Complete Phase 5 (US3) — bootstrap CI corrected.
6. **STOP and VALIDATE**: run the existing test suite + new US1–US3 tests + a manual audit. Confirm scores shift in the expected direction. This is the MVP — algorithm v2 is statistically defensible at this point.
7. Bump SCORING_THRESHOLDS_VERSION to 2.0.0; CHANGELOG entry. Ship as v2.0.0-rc1.

### Incremental Delivery (P2 + P3 stories as follow-up PRs)

Each P2/P3 story is a separate small PR that builds on the MVP:

- US4 (Opening book): standalone PR, clean book exclusion.
- US5 (Per-segment): builds on US1, adds phase weighting.
- US6 (Timing): standalone PR if US1 is in.
- US7 (CUSUM): builds on US1.
- US8 (Rating calibration): builds on Phase 2.

### Parallel Team Strategy

Phase 1 + Phase 2 done by one developer (foundational). Then:

- Developer A: US1 → US2 → US3 (P1 chain, becomes MVP)
- Developer B: US4 (parallel to US1, independent)
- Developer C: US6 (parallel to US1, independent)
- After US1 lands: any developer picks up US5, US7, US8.

---

## Notes

- [P] tasks = different files, no dependencies.
- [Story] label maps task to specific user story for traceability.
- Each user story is independently completable and testable post-Phase 2.
- Verify each test fails before implementing (constitution Principle II: red → green → refactor).
- Commit after each task or logical group; use Spec Kit commit prefix.
- Stop at any checkpoint to validate story independently.
- Avoid: vague tasks, same-file conflicts on shared files like `aggregator.py` (T016, T023, T043 all touch it — serialize them or fold into one commit per touch).
