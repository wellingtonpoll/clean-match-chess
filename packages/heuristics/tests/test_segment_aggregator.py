"""Per-segment aggregation + phase-weighted score (T029, FR-013-015, SC-006).

Covers US5 AS2 + AS3:
  AS2: phase weighting active — TACTICAL-concentrated scores higher
       than ENDGAME-concentrated for identical aggregate signals.
  AS3: Σ score_contribution == game_score within float tolerance.
"""

from __future__ import annotations

import math

from heuristics.rating_baselines import get_baselines
from heuristics.scoring.segment_aggregator import (
    PHASE_WEIGHTS,
    aggregate_segments,
)
from shared_types.game import (
    CandidateMove,
    ComplexityScore,
    Move,
    MoveClassification,
    PlayerColor,
    Position,
)
from shared_types.signal import Phase, Segment


def _position(
    ply: int,
    *,
    eval_cp: int = 0,
    composite: float = 0.5,
    top_uci: str = "e2e4",
    is_book: bool = False,
) -> Position:
    return Position(
        ply=ply,
        fen=f"f-{ply}",
        side_to_move=PlayerColor.WHITE if ply % 2 == 0 else PlayerColor.BLACK,
        eval_cp=eval_cp,
        mate_in=None,
        top_moves=(
            CandidateMove(san="e4", uci=top_uci, eval_cp=eval_cp, mate_in=None, pv=(), rank=1),
        ),
        complexity=ComplexityScore(
            branching_factor=20.0,
            eval_volatility=0.0,
            tactical_density=0.0,
            move_ambiguity=0.05,
            composite=composite,
        ),
        is_critical=False,
        is_only_move=False,
        is_book=is_book,
    )


def _move(ply: int, *, uci: str = "e2e4", delta: int = 0) -> Move:
    return Move(
        ply=ply,
        san="e4",
        uci=uci,
        played_by=PlayerColor.WHITE if ply % 2 == 0 else PlayerColor.BLACK,
        time_spent_ms=None,
        eval_delta_cp=delta,
        classification=MoveClassification.GOOD,
    )


def _engine_perfect_block(start: int, length: int) -> tuple[tuple[Position, ...], tuple[Move, ...]]:
    """A block of `length` plies where the player always plays top_uci."""
    positions = tuple(
        _position(start + i, eval_cp=0, composite=0.4, top_uci="e2e4") for i in range(length)
    )
    moves = tuple(_move(start + i, uci="e2e4", delta=0) for i in range(length))
    return positions, moves


def _random_block(start: int, length: int) -> tuple[tuple[Position, ...], tuple[Move, ...]]:
    """A block where the player plays a non-top move."""
    positions = tuple(
        _position(start + i, eval_cp=0, composite=0.4, top_uci="e2e4") for i in range(length)
    )
    moves = tuple(_move(start + i, uci="g1f3", delta=-50) for i in range(length))
    return positions, moves


def test_phase_weights_constants_match_spec() -> None:
    """T033: phase weights are FR-014 / contract values, no drift."""
    assert PHASE_WEIGHTS[Phase.OPENING] == 0.5
    assert PHASE_WEIGHTS[Phase.MIDDLEGAME] == 1.0
    assert PHASE_WEIGHTS[Phase.TACTICAL] == 1.5
    assert PHASE_WEIGHTS[Phase.CONVERSION] == 1.3
    assert PHASE_WEIGHTS[Phase.ENDGAME] == 0.7


def _audit_score(
    layout: list[tuple[Phase, str]],
) -> tuple[float, tuple[Segment, ...]]:
    """Build positions/moves/segments matching ``layout`` and aggregate.

    Each layout entry is (phase, kind) with kind in {"perfect", "random"}
    and each block is 30 plies long.
    """
    block_len = 30
    positions: list[Position] = []
    moves: list[Move] = []
    segments: list[Segment] = []
    cursor = 0
    for phase, kind in layout:
        start = cursor
        if kind == "perfect":
            block_pos, block_mov = _engine_perfect_block(start, block_len)
        else:
            block_pos, block_mov = _random_block(start, block_len)
        positions.extend(block_pos)
        moves.extend(block_mov)
        segments.append(Segment(phase=phase, ply_range=(start, start + block_len)))
        cursor += block_len

    baselines = get_baselines()
    return aggregate_segments(
        tuple(segments),
        positions=tuple(positions),
        moves=tuple(moves),
        baselines=baselines,
        subject_rating=1500,
        subject_color=PlayerColor.WHITE,
    )


def test_tactical_concentration_outscores_endgame_concentration() -> None:
    """SC-006 / US5 AS2: TACTICAL-concentrated ≥ 30% higher than ENDGAME."""
    tactical_score, _ = _audit_score(
        [
            (Phase.OPENING, "random"),
            (Phase.MIDDLEGAME, "random"),
            (Phase.TACTICAL, "perfect"),
            (Phase.CONVERSION, "random"),
            (Phase.ENDGAME, "random"),
        ]
    )
    endgame_score, _ = _audit_score(
        [
            (Phase.OPENING, "random"),
            (Phase.MIDDLEGAME, "random"),
            (Phase.TACTICAL, "random"),
            (Phase.CONVERSION, "random"),
            (Phase.ENDGAME, "perfect"),
        ]
    )
    # TACTICAL phase weight 1.5; ENDGAME 0.7 → 2.14x ratio on the
    # contribution. Spec asks for ≥ 30% higher.
    assert tactical_score >= 1.3 * endgame_score, (
        f"tactical={tactical_score} endgame={endgame_score}"
    )


def test_score_contributions_sum_equals_game_score() -> None:
    """AS3 / contract: Σ score_contribution == game_score (float tol)."""
    score, segs = _audit_score(
        [
            (Phase.OPENING, "perfect"),
            (Phase.MIDDLEGAME, "random"),
            (Phase.TACTICAL, "perfect"),
        ]
    )
    total = sum(s.score_contribution for s in segs)
    assert math.isclose(total, score, abs_tol=1e-9), f"sum={total} score={score}"


def test_empty_segments_returns_zero() -> None:
    baselines = get_baselines()
    score, segs = aggregate_segments(
        (),
        positions=(),
        moves=(),
        baselines=baselines,
        subject_rating=None,
        subject_color=PlayerColor.WHITE,
    )
    assert score == 0.0
    assert segs == ()
