"""Determinism check (T049, FR-007).

Runs ``aggregate_score`` twice on identical inputs with the same seed
and asserts the SuspicionScore (including confidence_interval and
dominant_signals) is bit-identical.
"""

from __future__ import annotations

from heuristics.scoring import aggregate_score
from heuristics.scoring.aggregator import WEIGHTS
from shared_types.game import (
    ComplexityScore,
    Move,
    MoveClassification,
    PlayerColor,
    Position,
)
from shared_types.signal import SignalAggregate


def _agg(name: str, value: float = 0.5, samples: int = 10) -> SignalAggregate:
    return SignalAggregate(
        signal_name=name,
        signal_version="0.1.0",
        mean=value,
        weighted_mean=value,
        samples=samples,
    )


def _position(ply: int) -> Position:
    return Position(
        ply=ply,
        fen=f"f-{ply}",
        side_to_move=PlayerColor.WHITE,
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
        played_by=PlayerColor.WHITE,
        time_spent_ms=None,
        eval_delta_cp=0,
        classification=MoveClassification.GOOD,
    )


def _resample(positions, moves):
    mean = sum(1 for p in positions if p.ply % 3 == 0) / max(1, len(positions))
    return (
        SignalAggregate(
            signal_name="acpl-analysis",
            signal_version="1.0.0",
            mean=mean,
            weighted_mean=mean,
            samples=len(positions),
        ),
    )


def test_aggregate_score_bit_identical_for_same_seed() -> None:
    """Same inputs + same seed → bit-identical SuspicionScore."""
    signals = tuple(_agg(name) for name in WEIGHTS)
    n = 60
    positions = tuple(_position(i) for i in range(n))
    moves = tuple(_move(i) for i in range(n))
    a = aggregate_score(
        signals,
        positions=positions,
        moves=moves,
        bootstrap_samples=1000,
        seed=42,
        resample_signals=_resample,
    )
    b = aggregate_score(
        signals,
        positions=positions,
        moves=moves,
        bootstrap_samples=1000,
        seed=42,
        resample_signals=_resample,
    )
    assert a.model_dump() == b.model_dump()


def test_legacy_path_deterministic_for_same_seed() -> None:
    """Legacy contribution-bootstrap path also deterministic."""
    signals = tuple(_agg(name) for name in WEIGHTS)
    a = aggregate_score(signals, seed=7)
    b = aggregate_score(signals, seed=7)
    assert a.model_dump() == b.model_dump()
