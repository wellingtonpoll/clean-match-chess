# ACPL Signal Contract

`acpl-analysis` is a new heuristic signal emitted by `heuristics/acpl_analysis/__init__.py::acpl_signal()`.

## Inputs

- `positions: tuple[Position, ...]` — output of the engine analyzer for the analyzed plies.
- `moves: tuple[Move, ...]` — actual moves played, aligned 1:1 with positions. Each `Move.eval_delta_cp` must already be populated by the pipeline.
- `subject_color: PlayerColor` — which side is being audited.
- `subject_rating: int | None` — Elo rating of the subject extracted from PGN headers.
- `baselines: RatingBaselines` — bundled lookup table.

## Eligibility filter

A `(position, move)` pair is eligible if and only if:
- `position.is_book is False`
- `position.is_only_move is False`
- `move.played_by == subject_color`
- `move.eval_delta_cp is not None`

## Computation

1. Collect `losses = [max(0, -m.eval_delta_cp) for (p, m) in eligible_pairs]`. Each entry is the centipawn loss attributed to the played move (positive = lost CP).
2. Compute `observed_mean = mean(losses)` and `observed_stdev = stdev(losses)`.
3. Look up `bucket = baselines.bucket_for(subject_rating)`.
4. Compute `z = (bucket.expected_acpl_mean - observed_mean) / bucket.expected_acpl_stdev`.
5. Normalize to suspicion: `suspicion = max(0.0, min(1.0, z / 3.0))`.

## Output

A `SignalAggregate` with:

```python
SignalAggregate(
    signal_name="acpl-analysis",
    signal_version="1.0.0",
    mean=suspicion,           # The normalized [0, 1] suspicion value
    weighted_mean=suspicion,  # Same — no weighting variant for this signal in Phase 1
    samples=len(eligible_pairs),
)
```

## Silencing

If `len(eligible_pairs) < 10`, the signal is silenced — it returns an aggregate with `samples=0` and `mean=0.0`. The aggregator skips silenced signals (does not count them against `total_weight`).

## Determinism

Pure function: same inputs → same output. No RNG used in the signal itself.

## Edge cases

- All moves are book moves → silenced (samples=0).
- `eval_delta_cp` is None on every eligible move (engine analysis gaps) → silenced (samples=0).
- `subject_rating is None` → uses the `"rating-unknown"` bucket. The signal still emits a finite value.
- `subject_rating` out of plausible range (≤0 or >3500) → treated as None.
- `observed_stdev == 0.0` (all losses equal — typically all zeros): the z formula uses the BUCKET stdev as denominator, so this is well-defined.

## Test fixtures (mapped to spec acceptance scenarios)

- Engine-perfect game with subject_rating=1500, ACPL=10 → suspicion ≥ 0.65 (US1 AS1).
- Same PGN content with subject_rating=2700 → suspicion ≤ 0.45 (US1 AS2).
- 5-ply game (below silencing threshold) → samples=0, signal silenced.
