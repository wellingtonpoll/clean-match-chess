"""Blunder-suppression v2 (T019, FR-004, US2 AS1/AS2/AS3, SC-007).

Verifies the rewritten signal:

  AS1: complexity > 0.6 AND top_moves[1:] has candidate with
       (cand.eval_cp - pos.eval_cp) <= -200 AND played move's
       eval_delta_cp > -100 → counts as evaded → 1.0.
  AS2: zero qualifying positions → samples=0 (silenced).
  AS3: regression vs the old buggy implementation (the new value
       differs from the old, and the new value is the correct one
       per the FR-004 definition).
"""

from __future__ import annotations

from heuristics.behavioral_patterns import blunder_suppression
from shared_types.game import (
    CandidateMove,
    ComplexityScore,
    Move,
    MoveClassification,
    PlayerColor,
    Position,
)


def _complexity(composite: float) -> ComplexityScore:
    return ComplexityScore(
        branching_factor=20.0,
        eval_volatility=0.0,
        tactical_density=0.0,
        move_ambiguity=0.05,
        composite=composite,
    )


def _candidate(eval_cp: int, rank: int) -> CandidateMove:
    return CandidateMove(
        san=f"C{rank}",
        uci=f"a{rank}a{rank}",
        eval_cp=eval_cp,
        mate_in=None,
        pv=(),
        rank=rank,
    )


def _position(
    ply: int,
    *,
    eval_cp: int,
    composite: float,
    second_eval_cp: int | None,
) -> Position:
    top_moves: tuple[CandidateMove, ...]
    if second_eval_cp is None:
        top_moves = (_candidate(eval_cp, 1),)
    else:
        top_moves = (_candidate(eval_cp, 1), _candidate(second_eval_cp, 2))
    return Position(
        ply=ply,
        fen=f"synthetic-{ply}",
        side_to_move=PlayerColor.WHITE,
        eval_cp=eval_cp,
        mate_in=None,
        top_moves=top_moves,
        complexity=_complexity(composite),
        is_critical=False,
        is_only_move=False,
        is_book=False,
    )


def _move(ply: int, delta: int) -> Move:
    return Move(
        ply=ply,
        san=f"M{ply}",
        uci=f"b{ply}b{ply}",
        played_by=PlayerColor.WHITE,
        time_spent_ms=None,
        eval_delta_cp=delta,
        classification=MoveClassification.GOOD,
    )


def test_evaded_blunder_returns_1_0() -> None:
    """AS1: high complexity + top-2 is -250 + played delta -50 → evaded."""
    positions = (
        _position(0, eval_cp=50, composite=0.8, second_eval_cp=-200),
    )
    moves = (_move(0, delta=-50),)
    agg = blunder_suppression(positions, moves)
    assert agg.samples == 1
    assert agg.mean == 1.0


def test_not_evaded_returns_0_0() -> None:
    """Same setup, but the played move IS the blunder (delta -250)."""
    positions = (
        _position(0, eval_cp=50, composite=0.8, second_eval_cp=-200),
    )
    moves = (_move(0, delta=-250),)
    agg = blunder_suppression(positions, moves)
    assert agg.samples == 1
    assert agg.mean == 0.0


def test_no_qualifying_positions_silenced() -> None:
    """AS2: no expected-blunder positions → samples=0 (silenced)."""
    positions = (
        _position(0, eval_cp=20, composite=0.3, second_eval_cp=10),
        _position(1, eval_cp=20, composite=0.4, second_eval_cp=15),
    )
    moves = (_move(0, delta=0), _move(1, delta=0))
    agg = blunder_suppression(positions, moves)
    assert agg.samples == 0


def test_complexity_below_threshold_excluded() -> None:
    """Position with complexity == 0.6 (not > 0.6) does not qualify."""
    positions = (
        _position(0, eval_cp=50, composite=0.6, second_eval_cp=-300),
    )
    moves = (_move(0, delta=-50),)
    agg = blunder_suppression(positions, moves)
    assert agg.samples == 0


def test_only_top1_no_second_candidate_excluded() -> None:
    """No top_moves[1] → not an expected-blunder position."""
    positions = (
        _position(0, eval_cp=50, composite=0.9, second_eval_cp=None),
    )
    moves = (_move(0, delta=-50),)
    agg = blunder_suppression(positions, moves)
    assert agg.samples == 0


def test_regression_vs_old_buggy_behavior() -> None:
    """AS3 / SC-007.

    Old impl: ``sum(p.eval_cp is not None and abs(p.eval_cp) < 200)`` over
    high-complexity positions. A position with eval_cp=10 and high
    complexity would count as "suppressed" (|10| < 200) regardless of
    whether a blunder was AVAILABLE or AVOIDED — the bug.

    New impl: requires both (a) a blunder candidate exists and (b) the
    played move avoided it.

    Construct a position where the OLD code returned non-zero but the NEW
    code returns 0 (no qualifying second candidate).
    """
    positions = (
        _position(0, eval_cp=10, composite=0.9, second_eval_cp=None),
    )
    moves = (_move(0, delta=0),)
    new_agg = blunder_suppression(positions, moves)

    # Old behavior: 1 suppressed / 1 expected = 1.0; samples=1.
    old_expected = [p for p in positions if p.complexity and p.complexity.composite > 0.7]
    old_suppressed = sum(
        1 for p in old_expected
        if p.eval_cp is not None and abs(p.eval_cp) < 200
    )
    old_value = old_suppressed / len(old_expected) if old_expected else 0.0
    assert old_value == 1.0

    # New behavior: zero qualifying positions → silenced.
    assert new_agg.samples == 0
    assert new_agg.mean != old_value
