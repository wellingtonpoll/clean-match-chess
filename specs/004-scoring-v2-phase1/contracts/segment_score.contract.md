# Segment Score Contract

The new `heuristics/scoring/segment_aggregator.py` computes per-segment scores and aggregates them into the final game-level score with phase weighting.

## Per-segment heuristics

For each `Segment` in `segments`, the following heuristics MUST be invoked on the segment's slice of (positions, moves):

| Heuristic | Source module | Required |
|---|---|---|
| `engine-correlation/weighted` | `heuristics/engine_correlation` | Yes |
| `engine-correlation/top1` | `heuristics/engine_correlation` | Yes |
| `acpl-analysis` | `heuristics/acpl_analysis` | Yes |
| `behavioral-patterns/blunder-suppression` | `heuristics/behavioral_patterns` | Yes |
| `timing-analysis` | `heuristics/timing_analysis` | Conditional — only when `time_spent_ms` is populated on ≥ 50% of segment moves |

Game-level only (NOT per-segment): `regime-shift` (operates on the full ACPL series), `complexity-analysis` (game-mean), `tactical-detection` (game-mean), `engine-correlation/top3` (game-mean — too sparse per segment), `behavioral-patterns/precision-burst` (cross-segment by definition).

## Per-segment aggregation

For each segment:

1. Run the per-segment heuristics on the segment's plies.
2. Apply §Normalization (below) to engine-correlation signals.
3. Compute the segment's `raw_aggregate` using the SAME `WEIGHTS` dict as the game-level aggregator but renormalized to the subset of signals present in that segment.

```
raw_aggregate = Σ (WEIGHTS[s] × signal_value[s]) / Σ WEIGHTS[s]   over signals present
```

4. Store the per-segment signals in `segment.signals`.

## §Normalization (engine-correlation ratio → suspicion score)

All three engine-correlation match-rate ratios (top-1, weighted-top-1, top-3) are normalized to a [0, 1] suspicion score using piecewise linear mapping centered at the rating-bucket baseline:

```python
import numpy as np

def ratio_to_score(ratio: float) -> float:
    """
    Maps observed/expected match-rate ratio to a [0, 1] suspicion score.

    ratio = 1.0  → score = 0.0  (matches baseline; no suspicion contribution)
    ratio = 2.5  → score = 1.0  (maximum suspicion)
    ratio < 1.0  → score = 0.0  (clamped; below-expectation play not penalized)
    """
    return float(np.clip((ratio - 1.0) / 1.5, 0.0, 1.0))
```

The same function is applied to top-1, weighted-top-1, and top-3 ratios. If the rating bucket lookup does not include an expected top-3 rate, the top-3 SignalAggregate is emitted with `samples=0` (silenced) and excluded from the weighted mean.

## Phase weights

```python
PHASE_WEIGHTS: dict[SegmentPhase, float] = {
    SegmentPhase.OPENING: 0.5,
    SegmentPhase.MIDDLEGAME: 1.0,
    SegmentPhase.TACTICAL: 1.5,
    SegmentPhase.CONVERSION: 1.3,
    SegmentPhase.ENDGAME: 0.7,
}
```

## Game-level aggregation

```
total_weight = Σ PHASE_WEIGHTS[seg.phase]              over segments present
game_score   = Σ (PHASE_WEIGHTS[seg.phase] × seg.raw_aggregate) / total_weight
```

`game_score` is then clamped to `[0.0, 1.0]`.

Each segment's `score_contribution` is recorded as `PHASE_WEIGHTS[seg.phase] × seg.raw_aggregate / total_weight`. Sum of `score_contribution` across all segments equals `game_score` within floating-point tolerance.

## Output

- `AuditRun.score` (top-level) — the game_score above.
- `Segment.signals` (per segment) — populated tuple.
- `Segment.score_contribution` (per segment) — populated float.

## Game-level signals (not per-segment)

The following signals still run on the entire game and are aggregated alongside the segment-weighted score:

- `regime-shift` (CUSUM over full ACPL series)
- `behavioral-patterns/precision-burst` (longest top-1 streak across game)
- `complexity-analysis`, `tactical-detection`, `engine-correlation/top3` (game-mean)

These contribute via the existing `WEIGHTS` dict in `scoring/aggregator.py`. The final game-level score is the WEIGHTED MEAN of (segment-weighted score, game-level-only signals) — the segment-weighted score gets its weight equal to the SUM of per-segment-applicable signal weights; game-level-only signals keep their individual weights.

## Edge cases

- Game has only one segment phase (e.g., a 15-ply blitz draw with only OPENING) → segment-weighted score equals that segment's raw_aggregate. The `total_weight` is just `PHASE_WEIGHTS[OPENING] = 0.5`, but the renormalization makes the result still in [0,1].
- Segment is too short for some heuristics (e.g., a 3-ply TACTICAL segment) → those heuristics silence themselves (samples=0); the segment's raw_aggregate uses only the signals that did fire.
- All segments are silenced (game is fully OPENING+book) → game_score = 0.0; the report should note "insufficient non-book material to score".

## Determinism

Pure function chain. Reproducibility preserved.

## Test fixtures (mapped to spec acceptance scenarios)

- Two synthetic AuditRuns: identical aggregate engine-correlation, signals concentrated in TACTICAL vs ENDGAME → TACTICAL-concentrated scores ≥ 30% higher (SC-006 / US5 AS2).
- Single-segment game → no crash, score finite (edge case).
