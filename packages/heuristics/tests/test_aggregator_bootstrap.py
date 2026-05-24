"""Bootstrap CI tests (T022, FR-007, US3 AS1/AS2/AS3, SC-004).

Covers the move-resampling bootstrap:

  AS1: 120-ply synthetic input → CI width ≤ 0.20.
  AS2: 25-ply input with similar signal means → CI width ≥ 1.5x the
       120-ply width.
  AS3: bit-identical CI for the same seed (reproducibility).
  Edge: 5 moves (below the degenerate threshold) → CI == (0.0, 1.0).
"""

from __future__ import annotations

from heuristics.scoring import aggregate_score
from heuristics.scoring.aggregator import BOOTSTRAP_SAMPLES_DEFAULT
from shared_types.game import (
    ComplexityScore,
    Move,
    MoveClassification,
    PlayerColor,
    Position,
)
from shared_types.signal import SignalAggregate


def _position(ply: int) -> Position:
    return Position(
        ply=ply,
        fen=f"f-{ply}",
        side_to_move=PlayerColor.WHITE if ply % 2 == 0 else PlayerColor.BLACK,
        eval_cp=0,
        mate_in=None,
        top_moves=(),
        complexity=ComplexityScore(
            branching_factor=20.0,
            eval_volatility=0.0,
            tactical_density=0.0,
            move_ambiguity=0.05,
            composite=0.4,
        ),
        is_critical=False,
        is_only_move=False,
        is_book=False,
    )


def _move(ply: int) -> Move:
    return Move(
        ply=ply,
        san=f"M{ply}",
        uci=f"a{ply}a{ply}",
        played_by=PlayerColor.WHITE if ply % 2 == 0 else PlayerColor.BLACK,
        time_spent_ms=None,
        eval_delta_cp=0,
        classification=MoveClassification.GOOD,
    )


def _binary_resample_factory(per_move_values: list[float]):
    """Resample function returning a single SignalAggregate (acpl-analysis).

    Resampling indices are taken from positions/moves identity; the test
    callback computes the empirical mean over the resampled subset using
    the stored per-move scalar values.
    """

    def _resample(
        positions: tuple[Position, ...],
        moves: tuple[Move, ...],
    ) -> tuple[SignalAggregate, ...]:
        # Map each (position, move) back to its per-move value by ply.
        # Multiple resampled plies may share the same ply index — that is
        # the bootstrap with replacement.
        vals = [per_move_values[p.ply] for p in positions]
        if not vals:
            mean = 0.0
        else:
            mean = sum(vals) / len(vals)
        return (
            SignalAggregate(
                signal_name="acpl-analysis",
                signal_version="1.0.0",
                mean=mean,
                weighted_mean=mean,
                samples=len(vals),
            ),
        )

    return _resample


def _signals_for(per_move_values: list[float]) -> tuple[SignalAggregate, ...]:
    mean = sum(per_move_values) / len(per_move_values)
    return (
        SignalAggregate(
            signal_name="acpl-analysis",
            signal_version="1.0.0",
            mean=mean,
            weighted_mean=mean,
            samples=len(per_move_values),
        ),
    )


def test_bootstrap_default_samples_is_10000() -> None:
    assert BOOTSTRAP_SAMPLES_DEFAULT == 10000


def test_long_game_ci_width_under_020() -> None:
    """AS1: 120-ply game → CI width ≤ 0.20."""
    n = 120
    # Mean ~ 0.5 (alternating 0/1) → high per-move variance but the
    # bootstrap of N=120 still produces a tight CI.
    per_move = [(i % 2) * 1.0 for i in range(n)]
    positions = tuple(_position(i) for i in range(n))
    moves = tuple(_move(i) for i in range(n))
    score = aggregate_score(
        _signals_for(per_move),
        positions=positions,
        moves=moves,
        bootstrap_samples=2000,
        seed=42,
        resample_signals=_binary_resample_factory(per_move),
    )
    lo, hi = score.confidence_interval
    assert hi - lo <= 0.20, f"width={hi - lo}"


def test_short_game_ci_width_at_least_1_5x_long() -> None:
    """AS2: 25-ply CI width ≥ 1.5x 120-ply CI width for similar mean."""
    short_n = 25
    long_n = 120
    short_per_move = [(i % 2) * 1.0 for i in range(short_n)]
    long_per_move = [(i % 2) * 1.0 for i in range(long_n)]

    short_score = aggregate_score(
        _signals_for(short_per_move),
        positions=tuple(_position(i) for i in range(short_n)),
        moves=tuple(_move(i) for i in range(short_n)),
        bootstrap_samples=2000,
        seed=42,
        resample_signals=_binary_resample_factory(short_per_move),
    )
    long_score = aggregate_score(
        _signals_for(long_per_move),
        positions=tuple(_position(i) for i in range(long_n)),
        moves=tuple(_move(i) for i in range(long_n)),
        bootstrap_samples=2000,
        seed=42,
        resample_signals=_binary_resample_factory(long_per_move),
    )
    short_w = short_score.confidence_interval[1] - short_score.confidence_interval[0]
    long_w = long_score.confidence_interval[1] - long_score.confidence_interval[0]
    assert short_w >= 1.5 * long_w, f"short={short_w} long={long_w}"


def test_bootstrap_is_deterministic_for_same_seed() -> None:
    """AS3: identical seed → bit-identical CI bounds."""
    n = 60
    per_move = [(i % 3) / 2.0 for i in range(n)]
    positions = tuple(_position(i) for i in range(n))
    moves = tuple(_move(i) for i in range(n))
    a = aggregate_score(
        _signals_for(per_move),
        positions=positions,
        moves=moves,
        bootstrap_samples=1000,
        seed=7,
        resample_signals=_binary_resample_factory(per_move),
    )
    b = aggregate_score(
        _signals_for(per_move),
        positions=positions,
        moves=moves,
        bootstrap_samples=1000,
        seed=7,
        resample_signals=_binary_resample_factory(per_move),
    )
    assert a.confidence_interval == b.confidence_interval


def test_degenerate_short_input_returns_widest_ci() -> None:
    """Edge: N < 5 plies → CI clipped to (0.0, 1.0) (spec edge case)."""
    n = 4
    per_move = [0.5] * n
    positions = tuple(_position(i) for i in range(n))
    moves = tuple(_move(i) for i in range(n))
    score = aggregate_score(
        _signals_for(per_move),
        positions=positions,
        moves=moves,
        bootstrap_samples=1000,
        seed=0,
        resample_signals=_binary_resample_factory(per_move),
    )
    assert score.confidence_interval == (0.0, 1.0)
