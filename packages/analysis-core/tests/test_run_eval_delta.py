"""Eval-delta-cp population tests (T012, FR-001).

Verifies `_populate_eval_deltas` follows the side-to-move sign
convention: positive delta means the played move improved the player's
position.

`Position.eval_cp` is from side-to-move perspective at that position.
Move played from `positions[i]` is by the side-to-move at `positions[i]`.
Post-move position `positions[i+1]` has the opposite side-to-move, so the
post-move eval from the player's perspective is `-positions[i+1].eval_cp`.

Hermetic: builds synthetic Position records directly, no Stockfish.
"""

from __future__ import annotations

from analysis_core.pipeline.run import _populate_eval_deltas
from shared_types.game import (
    ComplexityScore,
    Move,
    MoveClassification,
    PlayerColor,
    Position,
)


def _position(ply: int, eval_cp: int | None, side: PlayerColor) -> Position:
    return Position(
        ply=ply,
        fen=f"synthetic-ply-{ply}",
        side_to_move=side,
        eval_cp=eval_cp,
        mate_in=None,
        top_moves=(),
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


def _move(ply: int, played_by: PlayerColor) -> Move:
    return Move(
        ply=ply,
        san=f"M{ply}",
        uci="e2e4",
        played_by=played_by,
        eval_delta_cp=0,
        classification=MoveClassification.GOOD,
    )


def test_winning_move_has_positive_delta() -> None:
    # White plays from a position eval +20 (white's POV), then black is
    # to move with eval -100 (black's POV, meaning white is up 100).
    # White's POV delta = -(-100) - 20 = 80 > 0.
    positions = (
        _position(0, 20, PlayerColor.WHITE),
        _position(1, -100, PlayerColor.BLACK),
    )
    moves = (_move(0, PlayerColor.WHITE),)
    out = _populate_eval_deltas(positions, moves)
    assert out[0].eval_delta_cp == 80


def test_losing_move_has_negative_delta() -> None:
    # White was up +20; after the blunder, black-to-move sees +300
    # (black is up 300). White's POV: -(300) - 20 = -320.
    positions = (
        _position(0, 20, PlayerColor.WHITE),
        _position(1, 300, PlayerColor.BLACK),
    )
    moves = (_move(0, PlayerColor.WHITE),)
    out = _populate_eval_deltas(positions, moves)
    assert out[0].eval_delta_cp == -320


def test_none_eval_yields_zero_delta() -> None:
    positions = (
        _position(0, None, PlayerColor.WHITE),
        _position(1, -50, PlayerColor.BLACK),
    )
    moves = (_move(0, PlayerColor.WHITE),)
    out = _populate_eval_deltas(positions, moves)
    assert out[0].eval_delta_cp == 0


def test_six_ply_sequence_signs() -> None:
    # 6-ply game. Evals chosen so we can predict each side's delta.
    # All evals are "from side-to-move perspective":
    #   ply 0 (W to move): +10
    #   ply 1 (B to move): -50  → W improved: -(-50) - 10 = 40
    #   ply 2 (W to move): -40  → B's POV at 2 is +40 (B improved): -(-40) - 50 = 90
    #     (B's delta = -(positions[2].eval_cp) - positions[1].eval_cp = -(-40) - (-50) = 90 ✓)
    #   ply 3 (B to move): +20  → W's delta = -(20) - (-40) = 20
    #   ply 4 (W to move): -10  → B's delta = -(-10) - 20 = -10 (B lost ground)
    #   ply 5 (B to move): +60  → W's delta = -(60) - (-10) = -50 (W blunder)
    positions = (
        _position(0, 10, PlayerColor.WHITE),
        _position(1, -50, PlayerColor.BLACK),
        _position(2, -40, PlayerColor.WHITE),
        _position(3, 20, PlayerColor.BLACK),
        _position(4, -10, PlayerColor.WHITE),
        _position(5, 60, PlayerColor.BLACK),
    )
    moves = (
        _move(0, PlayerColor.WHITE),
        _move(1, PlayerColor.BLACK),
        _move(2, PlayerColor.WHITE),
        _move(3, PlayerColor.BLACK),
        _move(4, PlayerColor.WHITE),
    )
    out = _populate_eval_deltas(positions, moves)
    deltas = [m.eval_delta_cp for m in out]
    assert deltas == [40, 90, 20, -10, -50]


def test_moves_beyond_positions_are_passed_through_unchanged() -> None:
    positions = (_position(0, 0, PlayerColor.WHITE),)
    moves = (
        _move(0, PlayerColor.WHITE),  # no positions[1] available
    )
    out = _populate_eval_deltas(positions, moves)
    # Default eval_delta_cp=0; pass-through leaves it unchanged.
    assert out[0].eval_delta_cp == 0
