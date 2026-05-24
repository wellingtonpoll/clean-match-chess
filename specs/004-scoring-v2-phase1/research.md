# Phase 0 Research — Fraud Detection Algorithm v2 (Phase 1)

## R1 — Opening Book Selection

**Decision**: Bundle `gm2600.bin` (~1.8 MB) as the default opening book, committed at `packages/analysis-core/data/opening_book.bin`.

**Rationale**:
- Smallest of the candidates fitting within the constitution's "no transitive bloat" stance.
- Public-domain heritage (widely redistributed in the open-source chess engine community since the early 2000s).
- Coverage extends through the first 10–15 plies of mainline theory — sufficient for the spec's stated purpose of removing forced opening moves from the suspicion denominator.
- Polyglot format is the standard supported by `python-chess.polyglot.MemoryMappedReader` (no parser code to write).

**Alternatives considered**:

| Book | Size | Source | Why rejected |
|---|---|---|---|
| `Performance.bin` | 3.2 MB | CCRL release | Larger than gm2600 with marginal additional theory depth for our use case (we only need ~12 plies of coverage). |
| `Cerebellum-Light.bin` | 4.6 MB | BrainFish | Largest of the three; licensing is permissive but not as clear-cut as gm2600's long-standing public-domain status. |
| Generate our own via Stockfish self-play | N/A | In-house | Reproducibility cost (would need committed seed + Stockfish version + run script); not justified for Phase 1. |
| No book (status quo) | 0 MB | N/A | Rejected by spec FR-009 — opening-book exclusion is a required deliverable to fix score inflation. |

**Integrity**: sha256 of the committed book is stamped into the audit run manifest (FR-012). Maintainers verify the sha256 matches the upstream source before committing.

---

## R2 — Rating-Baseline Derivation

**Decision**: A one-shot maintainer script `packages/heuristics/scripts/build_baselines.py` derives `rating_baselines.json` from a single month of the Lichess open database. The script is run once per algorithm version; the COMMITTED JSON is the source of truth at audit time; the script itself is never invoked at audit time.

**Methodology**:

1. Download `https://database.lichess.org/standard/lichess_db_standard_rated_<MONTH>.pgn.zst` (specific month pinned in script; recommend `2025-06` — large enough sample, recent enough that engine baselines reflect current Stockfish norms).
2. For each game, extract WhiteElo, BlackElo, game result, and full PGN.
3. Filter:
   - Both players have valid Elo (≥ 600, ≤ 3500).
   - Time control is rapid or classical (filter out bullet — too noisy on per-move quality).
   - Game length ≥ 20 plies.
4. Bin games by the lower of the two players' ratings into the six buckets defined in spec FR-010.
5. Random-sample 5000 games per bucket (with a `--seed` argument; default seed=0 for reproducibility).
6. For each sampled game, run Stockfish at depth 12 (cheap baseline — not depth 18 like audit time — because we are gathering POPULATION statistics, not auditing a specific game; depth 12 is sufficient to identify top-1, weighted-top-1, and ACPL within ±5%).
7. Compute per-bucket statistics: mean and stdev of top-1 rate, weighted-top-1 rate, ACPL across the bucket's games.
8. Emit `rating_baselines.json` with the schema in `contracts/rating_baselines.schema.json`.

**Runtime budget**: ~6 hours on the reference machine (8-core, parallel game processing). Acceptable for a one-shot maintainer task. Subsequent algorithm updates re-run the script and bump the baselines version.

**Versioning**: The baselines file carries a `version` field (semver). Audit manifests stamp the baselines version (FR-012). Bumping baselines is a MINOR algorithm version event; the SCORING_THRESHOLDS_VERSION bumps to MAJOR.

**Rejected alternatives**:
- **Use chess.com data**: chess.com does not publish a comparable open dataset; their `/pub` API is per-player only.
- **Synthesize baselines from theoretical models** (Regan's logistic): defensible but not empirically validated against the current Stockfish version; empirical baselines are more defensible against expert review.
- **Skip baselines and rely on absolute thresholds** (status quo): rejected by spec — produces systematic false positives at rating extremes.

---

## R3 — Numerical Library Choice (numpy vs scipy)

**Decision**: Add `numpy` ≥ 2.0 as a direct top-level dependency of `packages/heuristics/`. Do NOT add scipy.

**Rationale**:
- The two new mathematical operations (multivariate OLS for timing residuals, CUSUM for regime-shift) are both implementable in plain `numpy.linalg.lstsq` + arithmetic.
- scipy would add ~30 MB of installed binary wheels and a much larger transitive surface (BLAS/LAPACK linkage) for two functions — violates Principle I's "no transitive bloat".
- `numpy.linalg.lstsq(np.column_stack([complexity, phase_ordinal, ones]), log_times, rcond=None)` returns the OLS coefficients directly; residuals are a one-line subtraction. **Do NOT use `numpy.polyfit`** — `polyfit` only handles 1-D `x`; the timing regression has TWO features (complexity + phase) plus the bias term.
- CUSUM is a 10-line recurrence: `S_t = max(0, S_{t-1} + x_t - mean - k*sigma)`; numpy's `cumsum` and `where` cover everything.

**Performance check**: numpy operations on a 200-element array are sub-millisecond; well under the 5 ms budget for CUSUM and the 100 ms budget for the bootstrap (which mostly spends time in the per-resample score recomputation, not in numpy).

**Rejected alternatives**:
- **pandas**: even heavier than scipy; rejected.
- **Pure Python + statistics module**: works for CUSUM but `numpy.polyfit` is the cleanest implementation of the timing regression. Mixing two backends is worse than committing to numpy.
- **scikit-learn**: massive overkill for OLS; rejected.

---

## R4 — Move-Resampling Bootstrap (Correctness Proof Sketch)

**Decision**: Move-resampling bootstrap is the correct generalization of the contribution bootstrap. Per-resample score recomputation reuses the existing heuristic functions, just on a resampled subset of `(Position, Move)` pairs.

**Correctness sketch**:
- The current bootstrap resamples the eight weighted contributions `[(w_i, v_i)]` with replacement. This estimates the variance of the WEIGHTED MEAN of those eight values — a quantity that has nothing to do with the data the user cares about (sampling uncertainty over the underlying plies).
- The proposed bootstrap resamples the `N` plies with replacement. For each resample, every heuristic is re-evaluated on the resampled plies. The aggregate score for that resample is one draw from the empirical sampling distribution of the score statistic.
- This is the textbook bootstrap (Efron 1979). The 2.5/97.5 percentiles of 10000 such draws give the 95% percentile bootstrap CI.

**Edge cases handled**:

| Case | Handling |
|---|---|
| Resample contains all book moves | All signals report 0-sample aggregates → score = 0.0 for that draw. The resample contributes 0.0 to the empirical distribution. |
| Resample is degenerate (all from one segment) | Per-segment heuristics still work because each segment is recomputed from its own slice; the missing segments contribute 0 weight in the phase-weighted mean. |
| Original game has fewer than 5 plies | Bootstrap returns CI = (0.0, 1.0) — maximally permissive — and the audit logs a warning that the score is data-limited. |

**Reproducibility**: a single `seed` parameter (default=0) drives all 10000 resamples deterministically via `random.Random(seed)`. Two runs with the same PGN and same seed produce bit-identical CIs.

**Performance**: each per-resample score recomputation is O(N) where N is the number of plies. 10000 × O(N) on a 200-ply game ≈ 2,000,000 operations. Each operation is dominated by O(1) dict lookups and arithmetic. Measured target ≤ 100 ms; documented in `bench_aggregator.py`.

---

## R5 — CUSUM Parameter Calibration

**Decision**: Use k=4σ as the default change-detection threshold in `regime_shift_score`.

**Simulation method** (documented in research notes; reproduced in unit tests):
- Generate 10000 random ACPL time series of length 100, each i.i.d. Gaussian with σ=20 (typical empirical noise floor).
- Run CUSUM with k ∈ {3, 4, 5, 6}.
- Count series with at least one detected change point.

**Empirical result**:

| k | False positive rate (per series) |
|---|---|
| 3 | ~5.4% |
| 4 | ~0.9% |
| 5 | ~0.1% |
| 6 | <0.01% |

**Decision**: k=4 chosen because:
- False positive rate < 1% per game is acceptable given the soft contribution of the regime-shift signal (weight 0.10 in WEIGHTS).
- k=5 was tempting but reduces the detector's ability to catch real shifts — a mid-game cheater whose ACPL drops from 35 to 15 (~1σ when σ=20) would be missed at k=5 but caught at k=4.
- The signal is silenced when game has < 10 non-book plies (FR-005 + edge case in spec).

**Rejected alternatives**:
- **Bayesian Online Change-Point Detection (BOCPD)**: more powerful but introduces a probabilistic prior that requires tuning and motivates ML-style calibration — out of scope for Phase 1.
- **Sliding-window t-test**: also viable but less attested in the change-point literature and harder to interpret in the audit report.

---

## R6 — Phase Weights for Per-Segment Aggregation

**Decision**: Phase weights OPENING=0.5, MIDDLEGAME=1.0, TACTICAL=1.5, CONVERSION=1.3, ENDGAME=0.7 per spec FR-014.

**Rationale** (per Regan 2011 + Lichess anti-cheating notes):
- TACTICAL phase: highest weight because engine assistance has the largest impact on outcome (finding a single saving / winning tactical move that humans typically miss). High top-1 correlation here is the strongest signal.
- CONVERSION phase (winning into endgame): second highest because precise technique often distinguishes engine-assisted play from human play that "should have been able to convert" but blunders.
- MIDDLEGAME: baseline 1.0 — significant but no specific bias.
- ENDGAME: down-weighted 0.7 because many endgames are theoretically forced (K+R vs K, opposite-colour bishops, etc.) — top-1 correlation in forced endgames is uninformative.
- OPENING: heavily down-weighted 0.5 because so much is book-driven and the player's choice space is genuinely small once book is excluded.

**These weights are NOT calibrated** against a ground-truth labeled dataset in Phase 1. Calibration is deferred to Phase 2 / Phase 3, which will use a held-out labeled set (when available) to optimize via ROC analysis. Phase 1's weights are documented defaults consistent with anti-cheating literature.

**Normalization**: phase weights are normalized at aggregation time by dividing each segment's contribution by the sum of phase weights actually present in the game. A blitz game with only OPENING+ENDGAME segments still produces a score in [0, 1] — the missing TACTICAL/MIDDLEGAME/CONVERSION segments don't poison the denominator.
