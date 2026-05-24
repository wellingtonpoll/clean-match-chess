"""Engine-correlation v2 — rating-bucket calibration (T040, FR-008, US8).

Verifies:
  AS1: ratio = observed / expected (mean=observed, weighted_mean=ratio).
  AS2: all 6 rating buckets + rating-unknown queryable.
  AS3: missing rating → rating-unknown bucket used.
  US8 independent test: 1200-rated 75% top-1 vs 2700-rated 75% top-1 →
  ratios differ measurably.
"""

from __future__ import annotations

import pytest
from heuristics.engine_correlation import engine_correlation
from heuristics.rating_baselines import get_baselines
from shared_types.game import (
    CandidateMove,
    ComplexityScore,
    Move,
    MoveClassification,
    PlayerColor,
    Position,
)


def _position(ply: int, *, top_uci: str, second_uci: str = "h2h3") -> Position:
    return Position(
        ply=ply,
        fen=f"f-{ply}",
        side_to_move=PlayerColor.WHITE,
        eval_cp=0,
        mate_in=None,
        top_moves=(
            CandidateMove(san="e4", uci=top_uci, eval_cp=0, mate_in=None, pv=(), rank=1),
            CandidateMove(san="h3", uci=second_uci, eval_cp=-50, mate_in=None, pv=(), rank=2),
        ),
        complexity=ComplexityScore(
            branching_factor=20.0,
            eval_volatility=0.0,
            tactical_density=0.0,
            move_ambiguity=0.05,
            composite=0.5,
        ),
        is_critical=False,
        is_only_move=False,
        is_book=False,
    )


def _move(ply: int, *, uci: str) -> Move:
    return Move(
        ply=ply,
        san="X",
        uci=uci,
        played_by=PlayerColor.WHITE,
        time_spent_ms=None,
        eval_delta_cp=0,
        classification=MoveClassification.GOOD,
    )


def _make_75pct_top1_game(n: int = 40) -> tuple[tuple[Position, ...], tuple[Move, ...]]:
    """Build a game where the player plays top-1 75% of the time."""
    positions = []
    moves = []
    for i in range(n):
        positions.append(_position(i, top_uci="e2e4"))
        if i % 4 == 0:  # 25% non-top-1
            moves.append(_move(i, uci="h2h3"))
        else:
            moves.append(_move(i, uci="e2e4"))
    return tuple(positions), tuple(moves)


def test_calibrated_mode_sets_mean_to_raw_rate_and_weighted_to_ratio() -> None:
    """AS1: mean=observed, weighted_mean=ratio."""
    positions, moves = _make_75pct_top1_game()
    baselines = get_baselines()
    top1, _top3, _weighted = engine_correlation(
        positions, moves, subject_rating=1500, baselines=baselines,
    )
    # 30/40 = 0.75 observed top-1.
    assert abs(top1.mean - 0.75) < 1e-6
    bucket = baselines.bucket_for(1500)
    expected = bucket.expected_top1
    assert abs(top1.weighted_mean - (0.75 / expected)) < 1e-6


def test_top3_silenced_in_calibrated_mode() -> None:
    """No expected_top3 in baselines → top-3 aggregate silenced."""
    positions, moves = _make_75pct_top1_game()
    baselines = get_baselines()
    _top1, top3, _weighted = engine_correlation(
        positions, moves, subject_rating=1500, baselines=baselines,
    )
    assert top3.samples == 0


def test_missing_rating_uses_rating_unknown_bucket() -> None:
    """AS3: subject_rating=None → rating-unknown bucket."""
    positions, moves = _make_75pct_top1_game()
    baselines = get_baselines()
    top1_unknown, _, _ = engine_correlation(
        positions, moves, subject_rating=None, baselines=baselines,
    )
    bucket = baselines.for_label("rating-unknown")
    assert abs(top1_unknown.weighted_mean - (0.75 / bucket.expected_top1)) < 1e-6


@pytest.mark.parametrize("rating,label", [
    (800, "≤1200"),
    (1300, "1201-1500"),
    (1700, "1501-1800"),
    (1900, "1801-2100"),
    (2200, "2101-2400"),
    (2500, "2401+"),
])
def test_all_six_rated_buckets_queryable(rating: int, label: str) -> None:
    """AS2: every rated bucket plus rating-unknown is queryable."""
    baselines = get_baselines()
    bucket = baselines.bucket_for(rating)
    assert bucket.bucket_label == label


def test_low_rated_player_with_75pct_top1_has_high_ratio() -> None:
    """US8 independent test: 1200 with 75% top-1 → ratio ≥ baselinex1.5."""
    positions, moves = _make_75pct_top1_game()
    baselines = get_baselines()
    top1_low, _, _ = engine_correlation(
        positions, moves, subject_rating=1200, baselines=baselines,
    )
    top1_high, _, _ = engine_correlation(
        positions, moves, subject_rating=2700, baselines=baselines,
    )
    # The low-rated player's ratio must exceed the high-rated player's
    # ratio by a meaningful margin (≥ 1.5x) on the same observed rate.
    assert top1_low.weighted_mean >= 1.5 * top1_high.weighted_mean


def test_legacy_uncalibrated_mode_unchanged() -> None:
    """Without baselines, mean == weighted_mean == observed_rate."""
    positions, moves = _make_75pct_top1_game()
    top1, top3, _weighted = engine_correlation(positions, moves)
    assert top1.mean == top1.weighted_mean
    assert top3.samples == len(moves)
