# Feature Specification: Fraud Detection Algorithm v2 — Phase 1 (Statistical Foundation)

**Feature Branch**: `004-scoring-v2-phase1`

**Created**: 2026-05-24

**Status**: Draft

**Input**: User description: "Fraud Detection Algorithm v2 — Phase 1 (Statistical Foundation): refactor of fraud-detection scoring engine to fix algorithmic bugs and incompleteness identified in post-audit of feature 001. Internal-only refactor: no CLI flag changes, no user-facing UI changes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — ACPL Computation and Distribution Signal (Priority: P1)

An auditor running `cleanmatch audit-game` on a PGN file receives a score that incorporates Average Centipawn Loss (ACPL), the gold-standard metric used by FIDE anti-cheating (Ken Regan/CAPS), Lichess, and chess.com. The ACPL signal is compared against the distribution expected for the player's Elo rating bracket, so the same raw ACPL value produces different suspicion scores depending on the player's claimed rating.

**Why this priority**: ACPL is the single most-validated metric in academic chess anti-cheating literature. Without it the audit cannot be defended against expert review and produces systematic errors at the rating extremes (false positives for strong players, false negatives for weak players). The other heuristics in Phase 1 depend on `Move.eval_delta_cp` being populated, which this story delivers.

**Independent Test**: Audit a single PGN where one player plays at engine-perfect quality (ACPL ≈ 10) while reporting rating 1500 — the audit must return HIGH risk. Audit the same engine-perfect game with reported rating 2800 — the audit must return LOW or MEDIUM. The output JSON must contain `eval_delta_cp` on every move and an `acpl-analysis` signal with a finite, calibrated value.

**Acceptance Scenarios**:

1. **Given** a PGN of a 1500-rated player with ACPL ≤ 20 across 40 non-book moves, **When** the auditor runs `cleanmatch audit-game`, **Then** the report's `dominant_signals` list contains `acpl-analysis` and the score is at least 0.65.
2. **Given** the same PGN content but with rating header set to 2700, **When** the auditor runs `cleanmatch audit-game`, **Then** the score is at most 0.45 because the ACPL is plausible for that rating.
3. **Given** a persisted run from this audit, **When** the auditor inspects the JSON export, **Then** every `Move` entry has `eval_delta_cp` populated with a non-null integer (or 0 if no eval was available).

---

### User Story 2 — Blunder-Suppression Bug Fix (Priority: P1)

A maintainer reviewing the audit output sees that the `blunder-suppression` signal now reflects whether the player ACTUALLY avoided losing moves in critical positions (delta-based), rather than the current behaviour of simply checking that the post-move evaluation is calm.

**Why this priority**: The current implementation is a known bug producing tautological results — it measures "post-move position is not bad" rather than "player evaded a blunder", inflating the suppression signal for any game ending in a draw or balanced position. This corrupts every audit output in production today.

**Independent Test**: Replay a curated PGN containing exactly two positions where the second-best move loses ≥200cp ("expected blunder positions"). For the case where the player picked the only non-losing move, signal value must be 1.0. For the case where the player picked a losing move, signal value must be 0.0. The old implementation does NOT distinguish these cases — the new test must demonstrate the difference.

**Acceptance Scenarios**:

1. **Given** a position where complexity composite > 0.6 and at least one candidate move has eval delta ≤ -200 cp, **When** the player's actual move has eval delta > -100, **Then** the position counts as "blunder evaded" and contributes 1.0 to the signal numerator.
2. **Given** a game with zero qualifying expected-blunder positions, **When** the signal is computed, **Then** the signal aggregate has 0 samples and is silenced from the score (not counted).
3. **Given** a regression-test PGN that previously produced an incorrect non-zero signal value, **When** the new implementation runs on it, **Then** the signal value is 0.0 with a documented test asserting the difference vs the old behaviour.

---

### User Story 3 — Bootstrap Confidence Interval Statistical Correctness (Priority: P1)

An auditor reading the report sees a confidence interval whose width reflects the actual sampling uncertainty of the underlying game-move data, rather than the current behaviour where every CI is approximately (0.03, 0.66) regardless of game length.

**Why this priority**: The current bootstrap resamples 8 weighted-signal contributions, which is statistically meaningless (N=8). The CI is therefore the same for a 20-ply game as for a 200-ply game, which is wrong. Auditors and downstream consumers cannot interpret the current CI. This is a credibility and correctness issue.

**Independent Test**: Run the audit on a long game (≥120 plies) and a short game (≤30 plies) with similar mean signals. The long-game CI width must be at least 50% narrower than the short-game CI width. The new bootstrap must produce different CIs for different game lengths.

**Acceptance Scenarios**:

1. **Given** a game with 120 analyzed plies, **When** the score is aggregated, **Then** the 95% confidence interval has width at most 0.20.
2. **Given** a game with 25 analyzed plies, **When** the score is aggregated, **Then** the CI width is at least 1.5x the width of the 120-ply case for similar signal magnitudes.
3. **Given** a deterministic seed, **When** the audit is run twice, **Then** the confidence interval bounds are bit-identical (reproducibility preserved).

---

### User Story 4 — Opening Book Integration (Priority: P2)

An analyst sees that mandatory opening-theory moves are excluded from the audit signal so that the score reflects what happened OUTSIDE of book, where player decisions actually matter.

**Why this priority**: Opening-book moves trivially match Stockfish top-1 because both follow established theory. Including them in the audit denominator inflates engine-correlation scores by 10–25% in typical games. This produces systematic false positives for any player who follows mainstream openings. The fix is well-scoped (one library, one file integration) but lower urgency than the P1 bugs because it only inflates scores rather than producing nonsense.

**Independent Test**: Run the audit on a 60-ply game where the first 14 plies are mainline Italian Game. With book enabled, the engine-correlation signal must use 46 ply samples (60 - 14). With book disabled, it must use 60. The signal values must differ measurably.

**Acceptance Scenarios**:

1. **Given** a bundled polyglot-format opening book file in the analysis package, **When** the auditor runs `cleanmatch audit-game` without `--book` flag, **Then** the bundled default book is loaded and the `Position.is_book` field on the first ~12 plies of a standard PGN is `True`.
2. **Given** the `--book PATH` flag with a valid polyglot file, **When** the auditor runs the audit, **Then** the custom book is loaded in place of the default.
3. **Given** the auditor inspects the engine-correlation signal samples, **When** comparing pre-fix vs post-fix runs on the same PGN, **Then** the sample count is lower post-fix (book plies excluded) and the signal value is the same or lower.

---

### User Story 5 — Per-Segment Heuristic Application (Priority: P2)

An auditor sees that suspicion scores are weighted by game phase, so a player who is suspiciously perfect in the TACTICAL or CONVERSION phase (where engine help has the most impact on outcome) scores higher than a player who is perfect in the OPENING (book) or ENDGAME (theoretical) phase.

**Why this priority**: Currently the audit treats all phases identically. A player who is 100% engine-correlated during a forced endgame technique sequence (e.g., K+R vs K) and average elsewhere should score LOW because that phase is deterministic. The same player with 100% correlation during the TACTICAL phase should score HIGH. Without phase weighting, both produce identical output. This is a precision improvement, not a bug fix.

**Independent Test**: Construct two synthetic AuditRun objects with identical aggregate engine-correlation but different distributions across segments — one concentrated in TACTICAL, one in ENDGAME. After phase weighting, the TACTICAL-concentrated run must score at least 30% higher than the ENDGAME-concentrated run.

**Acceptance Scenarios**:

1. **Given** a game segmented into OPENING/MIDDLEGAME/TACTICAL/CONVERSION/ENDGAME, **When** signals are computed, **Then** each `Segment.signals` array is populated with per-phase heuristic outputs.
2. **Given** the same per-segment signals, **When** the game-level score is aggregated, **Then** it is the phase-weighted mean using weights OPENING=0.5x, MIDDLEGAME=1.0x, TACTICAL=1.5x, CONVERSION=1.3x, ENDGAME=0.7x.
3. **Given** a JSON export of an AuditRun, **When** the auditor inspects each `Segment`, **Then** `score_contribution` is non-null and the sum of weighted contributions equals the game-level score (within floating-point tolerance).

---

### User Story 6 — Timing Regression Signal (Priority: P2)

An auditor sees a timing signal that captures subtle anomalies — implausibly fast play in complex positions AND implausibly slow play in easy positions — based on regression residuals, not a binary fast-move count.

**Why this priority**: The current binary heuristic misses sophisticated cheating patterns (cheater takes "normal" time on easy moves to disguise, then uses engine on complex ones). Regression residuals capture both directions of anomaly. Lower priority because timing data is often missing or unreliable in PGN headers, so the signal contributes less than ACPL.

**Independent Test**: Construct a game where the player spends 30s on every easy-position move (residual: +1.5σ) but 200ms on every hard-position move (residual: -2.5σ). The new signal must classify >70% of hard-position moves as anomalies. The old binary heuristic detects only the hard-position fast moves and misses the easy-position slow play.

**Acceptance Scenarios**:

1. **Given** a PGN with `time_spent_ms` populated on at least 20 moves, **When** the signal is computed, **Then** the regression fit log(time_ms + 1) ~ complexity + phase produces residuals and the signal value is the fraction of moves with |residual| > 2 standard deviations.
2. **Given** a sub-signal for pre-moves (time < 300ms on non-trivial positions), **When** combined with the residual anomaly rate, **Then** the final signal value is `0.7 × residual_rate + 0.3 × premove_rate`.
3. **Given** a game with no timing data, **When** the signal is computed, **Then** the signal aggregate has 0 samples and is silenced (not counted in score).

---

### User Story 7 — Regime-Shift via CUSUM Change-Point Detection (Priority: P3)

An auditor sees that the regime-shift signal detects sudden changes in PLAY QUALITY (centipawn-loss series), not segment-size variation, so a player who starts a game playing normally and switches to engine usage mid-game is flagged.

**Why this priority**: Detects a specific high-value cheating pattern (mid-game engine activation) that the current segment-size heuristic does not address at all. P3 because it requires the ACPL series from US1 to be in place first and represents a narrower fraud pattern than the broad signals in P1/P2.

**Independent Test**: Construct a synthetic ACPL time series of [50,55,60,45,52, 8,5,7,4,6, ...] — a clear regime change at index 5 from ~50 mean to ~6 mean. The CUSUM detector with k=4σ must detect a change point in the range [4..7]. A flat series with no change must return zero change points.

**Acceptance Scenarios**:

1. **Given** a per-move ACPL series with 60+ samples and a true change point, **When** the CUSUM detector runs with k=4, **Then** at least one change point is detected and the signal value is non-zero.
2. **Given** a stationary ACPL series (constant mean, normal noise), **When** the detector runs, **Then** the expected number of false positives over 1000 random series is at most 1% of trials.
3. **Given** a game with fewer than 10 non-book plies, **When** the detector runs, **Then** the signal returns 0.0 with a 0-sample aggregate (silenced).

---

### User Story 8 — Rating-Bucket Calibration of Engine-Correlation (Priority: P3)

An auditor sees that engine-correlation match rates are interpreted relative to the player's expected match rate for their Elo rating bucket, so the signal stays useful across the full rating spectrum without producing systematic false positives for masters or false negatives for beginners.

**Why this priority**: Solves the same false-positive class as US1 (rating-blindness) but for the match-rate signal family. P3 because US1's ACPL signal subsumes most of the value — match-rate rating calibration is a defence-in-depth complement, not a primary signal.

**Independent Test**: Audit a game where a 2700-rated player plays 75% top-1 — the engine-correlation signal must return a ratio close to 1.0 (matches expectation). Audit a 1200-rated player with the same 75% top-1 — ratio must be ≥2.5 (massive over-performance). The lookup table must produce different expected values for the two ratings.

**Acceptance Scenarios**:

1. **Given** a player rating extracted from PGN headers (WhiteElo or BlackElo for the subject color), **When** the engine-correlation signal is computed, **Then** the signal value is the observed match rate divided by the expected match rate from the rating-bucket lookup table.
2. **Given** a rating bucket lookup table committed at `packages/heuristics/data/rating_baselines.json`, **When** any of the 6 expected buckets is queried (≤1200, 1201–1500, 1501–1800, 1801–2100, 2101–2400, 2401+), **Then** an expected top-1 rate and expected complexity-weighted top-1 rate are returned.
3. **Given** a PGN with missing rating headers, **When** the signal is computed, **Then** the "rating-unknown" bucket is used (defaulting to median expected values) and the audit succeeds without error.

---

### Edge Cases

- **Empty book**: If the bundled polyglot file is corrupt or absent, the audit must continue with `is_book=False` for all positions and log a warning (do not crash).
- **All-book game (draw by repetition in opening)**: If every analyzed ply is a book move, every signal that filters book positions must report a 0-sample aggregate; the score should fall back to a "low-data, low-suspicion" default rather than a NaN.
- **Single-segment game**: A 20-ply blitz game may produce only OPENING+ENDGAME segments. Per-segment heuristics must not assume all 5 segment phases exist.
- **Engine evaluation gaps**: If Stockfish times out on a position, `eval_cp` is None and `eval_delta_cp` must also be None for that move — downstream signals must handle the None gracefully.
- **Bootstrap with N<5 moves**: Move-resampling bootstrap with very few samples must clip the CI to the most permissive range `(0.0, 1.0)` rather than reporting a misleadingly narrow interval.
- **Unknown rating in synthesized PGN**: PGNs without WhiteElo / BlackElo headers must fall back to the "rating-unknown" bucket; signal values must remain bounded and the audit must complete.
- **Rating outside 1..3500 sanity range**: Treat impossible ratings (≤0, >3500) as missing and use the rating-unknown bucket. Log a warning.
- **CUSUM on monotonic series**: A series that monotonically improves throughout the game (a "learning" pattern) must NOT be flagged as a regime shift; the test must distinguish ramps from step changes.

## Requirements *(mandatory)*

### Functional Requirements

#### Algorithmic correctness

- **FR-001**: System MUST populate `Move.eval_delta_cp` for every analyzed move using the formula `eval_after_played - eval_before` from side-to-move perspective, expressed in centipawns where positive means the played move improved the player's position.
- **FR-002**: System MUST compute an ACPL (Average Centipawn Loss) value for the subject color analyzed in the audit, defined as the mean of `max(0, -eval_delta_cp)` over all non-book, non-only-move plies played by the subject. (The opposing color's ACPL is not computed or stored.)
- **FR-003**: System MUST emit a new `acpl-analysis` heuristic signal whose value is calibrated by player rating bucket and represents the suspicion that the observed ACPL is too low for the player's rating. Signal silenced (samples=0, excluded from weighted mean) when fewer than 10 eligible non-book non-only-move plies are available. See `contracts/acpl_signal.contract.md` for the full eligibility definition and silencing semantics.
- **FR-004**: System MUST rewrite `blunder_suppression` to define "expected blunder position" as `complexity.composite > 0.6 AND any candidate move in top_moves[1:] has eval_delta_cp ≤ -200`, and "evaded" as `actual move eval_delta_cp > -100`.
- **FR-005**: System MUST rewrite `regime_shift_score` to apply CUSUM change-point detection on the per-move ACPL time series with threshold k=4σ.
- **FR-006**: System MUST rewrite `timing_anomaly` to use regression residuals from `log(time_spent_ms + 1) ~ complexity.composite + segment_phase` rather than a binary fast-move count, combined with a pre-move sub-signal (fraction of non-trivial positions with `time_spent_ms < 300`). Phase encoding: ordinal integers `OPENING=0, MIDDLEGAME=1, TACTICAL=2, CONVERSION=3, ENDGAME=4`. Ordinal encoding is required (not one-hot) — assumes linear progression across phases, acceptable approximation given the 5-category natural ordering.
- **FR-007**: System MUST replace the contribution-bootstrap CI computation in `aggregate_score` with a move-resampling bootstrap that resamples positions/moves with replacement N=10000 times and recomputes the score per resample.
- **FR-008**: System MUST compute engine-correlation match rates per rating-bucket-calibrated ratio: observed rate ÷ expected rate from `packages/heuristics/data/rating_baselines.json`, where 1.0 means "matches rating expectation" and >1.0 means "exceeds expectation". The ratio is normalized to a [0, 1] suspicion score using piecewise linear mapping centered at the baseline:

  ```
  score = clip((ratio - 1.0) / 1.5, 0.0, 1.0)
  ```

  Semantics: ratio 1.0 → 0.0 (no suspicion contribution), ratio 2.5 → 1.0 (maximum suspicion), ratio < 1.0 → 0.0 (clamped; below-expectation play not penalized). This mapping applies identically to top-1, weighted-top-1, AND top-3 match rates. If the rating bucket lookup table does not include an expected top-3 rate, the top-3 signal is silenced (samples=0) and excluded from the weighted mean. The full normalization specification lives in `contracts/segment_score.contract.md` §Normalization.

#### Data and provenance

- **FR-009**: System MUST commit a polyglot-format opening book file (≤ 5 MB) under `packages/analysis-core/data/` and load it by default in `_analyse_positions`, setting `Position.is_book = True` when the book contains a non-trivial entry for the position.
- **FR-010**: System MUST commit a rating-baselines lookup table at `packages/heuristics/data/rating_baselines.json` with entries for 6 rating buckets (≤1200, 1201–1500, 1501–1800, 1801–2100, 2101–2400, 2401+) plus a "rating-unknown" fallback bucket, where each entry contains expected top-1 rate, expected weighted top-1 rate, expected ACPL mean, and expected ACPL standard deviation.
- **FR-011**: System MUST include a one-time generation script under `packages/heuristics/scripts/build_baselines.py` that derives the rating-baselines JSON from a documented public Lichess open-database month-export, with deterministic seed and reproducible output (the script is run by maintainers; the output JSON is the artifact committed).
- **FR-012**: System MUST stamp the new ACPL signal version, the regime-shift signal version, the timing signal version, and the rating-baselines version into the existing reproducibility manifest emitted with each audit run.

#### Phase-aware aggregation

- **FR-013**: System MUST populate `Segment.signals` for each segment in `Segment.phase` and compute heuristics (engine-correlation, ACPL, blunder-suppression, timing) per segment.
- **FR-014**: System MUST populate `Segment.score_contribution` as the phase-weighted contribution of that segment's signals to the game score, using weights OPENING=0.5, MIDDLEGAME=1.0, TACTICAL=1.5, CONVERSION=1.3, ENDGAME=0.7.
- **FR-015**: System MUST compute the final game-level score as the weighted mean of segment score contributions, normalized so the maximum possible score remains 1.0 (clamp + rescale).

#### Scoring weights

- **FR-016**: System MUST update `WEIGHTS` in `scoring/aggregator.py` to incorporate the new ACPL signal with weight 0.30 and reduce engine-correlation/top1 to 0.05, with the full new distribution: acpl-analysis 0.30, engine-correlation/weighted 0.30, engine-correlation/top1 0.05, engine-correlation/top3 0.05, regime-shift 0.10, behavioral-patterns/precision-burst 0.05, behavioral-patterns/blunder-suppression 0.05, complexity-analysis 0.03, tactical-detection 0.03, timing-analysis 0.04.
- **FR-017**: System MUST bump `SCORING_THRESHOLDS_VERSION` from `1.0.0` to `2.0.0` to reflect the breaking change in score semantics (existing persisted runs are no longer comparable to new runs). Note: `SCORING_THRESHOLDS_VERSION` is a misnomer — threshold numeric values (0.35/0.70) are unchanged in this phase (see FR-018); the constant tracks scoring-algorithm semantics. A rename to `SCORING_ALGORITHM_VERSION` is tracked as a follow-up cleanup (non-blocking for Phase 1).
- **FR-018**: System MUST preserve existing risk-level thresholds (LOW < 0.35, MEDIUM < 0.70, HIGH ≥ 0.70) in this phase; calibrated thresholds are out of scope for Phase 1 and deferred to a future phase. Note: SC-002's FPR target (≤ 2% at HIGH) is a calibration claim and is therefore deferred to Phase 2 alongside threshold calibration (see SC-002 demotion).

#### Backward compatibility and migration

- **FR-019**: System MUST keep the public Python API positional and required-argument surface of `analysis-core.pipeline.run_single_game` and `run_username_batch` unchanged. Additive optional keyword arguments with sensible defaults (`book_path: str | None = None` per T028) are permitted and do not constitute a breaking change. New kwargs MUST be documented in the function's docstring with type and default.
- **FR-020**: System MUST keep the CLI surface consistent. The existing `--book` flag (previously only on `audit_game`) is extended to `audit_username` so all subcommands that accept a game source accept `--book <path>`. No other new flags are introduced. Rationale: batch analysis must be reproducible with a custom book; silently defaulting to bundled book in batch mode would break power-user scripts and violate Principle III (UX Consistency).
- **FR-021**: System MUST preserve all existing JSON export schema keys; new keys (e.g., `Segment.signals`) may be added but no existing keys removed or renamed.
- **FR-022**: System MUST document in `CHANGELOG.md` the algorithm version bump from 1.x to 2.0.0 and the practical implications for users (scores from prior runs are not comparable).

### Key Entities

- **AcplSignal**: A new `SignalAggregate` produced by the `acpl-analysis` heuristic. Stores observed ACPL mean, expected ACPL mean for the player's rating bucket, observed standard deviation, and a normalized suspicion value [0,1] representing how many standard deviations below the expected mean the observed ACPL is.
- **RatingBaseline**: A static lookup entry keyed by rating bucket label. Contains expected top-1 match rate, expected weighted top-1 match rate, expected ACPL mean, expected ACPL standard deviation, and the sample size that produced the estimate.
- **OpeningBook**: A polyglot-format binary file describing position → move table. Used to mark known opening-theory moves so they can be excluded from suspicion signals.
- **CusumChangePoint**: A detected change-point event in the per-move ACPL time series. Records ply index, magnitude (cumulative deviation at detection), and direction (improvement vs regression).
- **SegmentScore**: A computed per-segment aggregate. Maps phase (OPENING/MIDDLEGAME/TACTICAL/CONVERSION/ENDGAME) to per-phase signal values and a weighted score contribution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 [DEFERRED — Phase 2]**: When auditing a curated set of 50 engine-assisted games played at simulated rating 1500, at least 45 (90%) produce a score ≥ 0.65 (MEDIUM or HIGH risk). Phase 1 gate: NOT ACTIVE. Corpus curation is tracked as Phase 2 backlog item P2-T001. Rationale: curated labeled datasets require sourcing and legal review outside Phase 1 scope. Pipeline correctness is validated by SC-003 through SC-010.
- **SC-002 [DEFERRED — Phase 2]**: When auditing a curated set of 50 known clean games played by FIDE-rated humans 2000–2400, no more than 1 (2%) produces a score ≥ 0.70 (HIGH risk) — establishing a false positive rate target of ≤ 2% at the HIGH threshold for this rating range. Phase 1 gate: NOT ACTIVE. See FR-018 resolution and Phase 2 backlog item P2-T002. Rationale: FPR measurement requires calibrated thresholds (FR-018 explicitly defers calibration to Phase 2).
- **SC-003**: For audits of games where the player rating is reliably extracted from PGN headers, the median score difference between identical move-content audits at simulated rating 1500 vs 2700 is at least 0.25 (demonstrates rating calibration is active).
- **SC-004**: The 95% confidence interval width on audits of games with ≥ 100 analyzed plies is at most 0.20 on average (vs current ≈0.60), confirming the new bootstrap produces tighter, more informative intervals on long games.
- **SC-005**: When auditing a PGN with the first 12 plies in mainstream opening book, the engine-correlation signal samples count decreases by at least 10 between pre-fix and post-fix runs on the same PGN, demonstrating book exclusion is active.
- **SC-006**: For two synthetic audits with identical aggregate engine-correlation but signals concentrated in TACTICAL vs ENDGAME, the TACTICAL-concentrated audit scores at least 30% higher than the ENDGAME-concentrated audit (demonstrates phase weighting is active).
- **SC-007**: The blunder-suppression unit-test suite includes at least one test case where the new implementation returns a different value from the old buggy implementation, with the test asserting the new value is the correct one per the FR-004 definition.
- **SC-008**: All existing unit-test suites in `packages/heuristics/tests/` and `packages/analysis-core/tests/` continue to pass with zero modifications other than expected updates to test fixtures that reflect the new signal definitions and weights.
- **SC-009**: The CHANGELOG.md entry for v2.0.0 explicitly states that scores from runs prior to this version are not numerically comparable, satisfying audit reproducibility documentation requirements.
- **SC-010**: The reproducibility manifest emitted by an audit includes the new signal versions (acpl-analysis, updated regime-shift, updated timing-analysis), the rating-baselines version, and the opening-book sha256.

## Assumptions

- The pipeline already produces `Position` objects with `complexity.composite` and `top_moves` populated by the existing `EngineAnalyzer`. Phase 1 builds on this output without modifying the analyzer.
- A small (≤ 5 MB) polyglot-format opening book is available under permissive license (e.g., the publicly distributed `Performance.bin` or equivalent). The exact book is a maintainer choice within that constraint.
- The Lichess open-database monthly export remains accessible at its current public URL for the maintainer-run baseline-generation script. The committed JSON is the artifact; the script is not run at audit time.
- Rating bucket bounds and phase weights are reasonable defaults from anti-cheating literature (Regan 2011, Regan/Haworth 2015). They are NOT calibrated against a ground-truth labeled dataset in Phase 1; ground-truth calibration is deferred to a later phase.
- The `--book` flag declared in `main.py` is currently a no-op and will not break any existing user workflow when it becomes functional.
- The `Move.eval_delta_cp` field is already present in the `shared_types.game.Move` dataclass; this feature populates it but does not change its declared type.
- Timing data (`time_spent_ms`) is available on roughly 50–80% of real-world PGNs; the timing-analysis signal silences itself when data is missing, which is acceptable.
- The bootstrap N=10000 with move resampling adds at most 100 ms overhead per game audit, which is acceptable relative to the 5–30 s spent in Stockfish analysis.
- Bumping `SCORING_THRESHOLDS_VERSION` to 2.0.0 invalidates numerical comparison with prior runs; downstream consumers of persisted runs are tolerant of this (verified in the CHANGELOG.md for the audit-run JSON schema).
- The bundled opening book and rating baselines are intentionally bundled rather than fetched at runtime, so the audit remains fully offline-capable.
- Phase 1 explicitly excludes the following from scope: Maia/Lc0 integration, multi-engine fingerprinting, longitudinal performance-shift signals, Bayesian aggregation with labeled-data priors, and any change to risk-level thresholds. Those are documented for a follow-on Phase 2 / Phase 3.
