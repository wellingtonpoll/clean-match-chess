"""Engine-correlation signal (T041)."""

from __future__ import annotations

import chess
from analysis_core.engine.analysis import StaticAnalyzer
from heuristics.engine_correlation import engine_correlation, signal_version
from shared_types.game import Move, MoveClassification, PlayerColor


def _make_moves(positions: tuple) -> tuple[Move, ...]:
    out: list[Move] = []
    for i, pos in enumerate(positions):
        top = pos.top_moves[0]
        out.append(
            Move(
                ply=i,
                san=top.san,
                uci=top.uci,
                played_by=PlayerColor.WHITE if i % 2 == 0 else PlayerColor.BLACK,
                eval_delta_cp=0,
                classification=MoveClassification.GOOD,
            )
        )
    return tuple(out)


def test_signal_version() -> None:
    assert signal_version().name == "engine-correlation"


def test_player_always_matches_top1() -> None:
    a = StaticAnalyzer()
    board = chess.Board()
    positions = tuple(a.analyse(board, ply=i) for i in range(5))
    moves = _make_moves(positions)
    top1, top3, _weighted = engine_correlation(positions, moves)
    assert top1.mean == 1.0
    assert top3.mean == 1.0


def test_no_eligible_positions_returns_zero() -> None:
    top1, top3, weighted = engine_correlation((), ())
    assert top1.mean == 0.0
    assert top3.mean == 0.0
    assert weighted.mean == 0.0
