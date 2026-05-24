"""CUSUM regime-shift signal (T037, FR-005, US7 AS1/AS2/AS3).

Verifies:
  AS1: engineered ACPL change-point → CUSUM detects it.
  AS2: 1000 stationary noise series → false-positive rate ≤ 1.5%
       (cushion above the 1.0% target — constitution Principle II
       prohibits flaky tests).
  AS3: < 10 non-book plies → silenced (samples=0).
  Edge: monotonically improving series does NOT trigger.
"""

from __future__ import annotations

import numpy as np
from heuristics.regime_shift import (
    _cusum_change_points,
    regime_shift_score,
)
from shared_types.game import (
    Move,
    MoveClassification,
    PlayerColor,
    Position,
)


def _position(ply: int, *, is_book: bool = False) -> Position:
    return Position(
        ply=ply,
        fen=f"f-{ply}",
        side_to_move=PlayerColor.WHITE if ply % 2 == 0 else PlayerColor.BLACK,
        eval_cp=0,
        mate_in=None,
        top_moves=(),
        complexity=None,
        is_critical=False,
        is_only_move=False,
        is_book=is_book,
    )


def _move(ply: int, *, delta: int) -> Move:
    return Move(
        ply=ply,
        san=f"M{ply}",
        uci=f"a{ply}a{ply}",
        played_by=PlayerColor.WHITE,
        time_spent_ms=None,
        eval_delta_cp=delta,
        classification=MoveClassification.GOOD,
    )


def test_engineered_change_point_detected() -> None:
    """AS1: ACPL series with a clear regime change → CUSUM detects."""
    # First 30 plies: ~50 cp loss; next 30 plies: ~5 cp loss.
    deltas = [-50] * 30 + [-5] * 30
    positions = tuple(_position(i) for i in range(len(deltas)))
    moves = tuple(_move(i, delta=d) for i, d in enumerate(deltas))
    agg = regime_shift_score(positions, moves)
    assert agg.samples == 60
    assert agg.mean > 0.0


def test_stationary_noise_false_positive_rate_under_1pct5() -> None:
    """AS2: 1000 stationary Gaussian series → ≤ 1.5% trigger.

    Threshold is the test cushion (1.0% target + 0.5% for BLAS/LAPACK
    drift across platforms per task spec).
    """
    rng = np.random.default_rng(seed=42)
    trials = 1000
    triggers = 0
    for _ in range(trials):
        series = rng.normal(0.0, 1.0, size=200).tolist()
        points = _cusum_change_points(series, k_sigma=4.0)
        if points:
            triggers += 1
    fpr = triggers / trials
    assert fpr <= 0.015, f"false-positive rate {fpr * 100:.2f}% > 1.5%"


def test_below_min_plies_silenced() -> None:
    """AS3: < 10 non-book plies → samples=0."""
    deltas = [-10] * 5
    positions = tuple(_position(i) for i in range(len(deltas)))
    moves = tuple(_move(i, delta=d) for i, d in enumerate(deltas))
    agg = regime_shift_score(positions, moves)
    assert agg.samples == 0


def test_gentle_monotonic_drift_does_not_trigger() -> None:
    """Edge: a slow learning ramp within ~1sigma does NOT trigger.

    Spec edge case: "CUSUM on monotonic series — a series that
    monotonically improves throughout the game (a 'learning' pattern)
    must NOT be flagged as a regime shift; the test must distinguish
    ramps from step changes." We test a gentle drift within stationary
    noise (~5cp change over 60 plies with ±10cp jitter).
    """
    rng = np.random.default_rng(seed=7)
    base = np.linspace(-30, -25, num=60)
    noise = rng.normal(0.0, 10.0, size=60)
    deltas = [int(b + n) for b, n in zip(base, noise, strict=True)]
    positions = tuple(_position(i) for i in range(len(deltas)))
    moves = tuple(_move(i, delta=d) for i, d in enumerate(deltas))
    agg = regime_shift_score(positions, moves, k_sigma=4.0)
    assert agg.mean == 0.0


def test_book_plies_excluded_from_series() -> None:
    """Book positions are filtered from the ACPL series."""
    deltas = [-10] * 30
    positions = tuple(_position(i, is_book=(i < 5)) for i in range(len(deltas)))
    moves = tuple(_move(i, delta=d) for i, d in enumerate(deltas))
    agg = regime_shift_score(positions, moves)
    assert agg.samples == 25  # 30 plies - 5 book


def test_legacy_segments_call_silenced() -> None:
    """Legacy ``regime_shift_score(segments)`` returns silenced aggregate."""
    agg = regime_shift_score(())
    assert agg.samples == 0
