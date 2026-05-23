"""Engine-analysis adapter contract (T037)."""

from __future__ import annotations

import chess
from analysis_core.engine.analysis import MAX_MULTIPV, Analyzer, StaticAnalyzer
from shared_types.game import PlayerColor


def test_static_analyzer_returns_position_at_initial_fen() -> None:
    a: Analyzer = StaticAnalyzer()
    board = chess.Board()
    pos = a.analyse(board, ply=0)
    assert pos.ply == 0
    assert pos.side_to_move is PlayerColor.WHITE
    assert pos.eval_cp == 0
    assert pos.top_moves


def test_static_analyzer_respects_multipv_cap() -> None:
    a = StaticAnalyzer(multipv=100)
    pos = a.analyse(chess.Board(), ply=0)
    assert len(pos.top_moves) <= MAX_MULTIPV


def test_static_analyzer_flags_only_move() -> None:
    # En prise + check forcing only move.
    fen = "k7/8/8/8/8/8/1Q6/K7 b - - 0 1"
    board = chess.Board(fen)
    pos = StaticAnalyzer().analyse(board, ply=0)
    legal_count = len(list(board.legal_moves))
    # Just assert is_only_move when there's exactly one legal move.
    assert pos.is_only_move is (legal_count == 1)


def test_static_analyzer_marks_check_as_critical() -> None:
    # Position where black is in check.
    fen = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
    board = chess.Board(fen)
    pos = StaticAnalyzer().analyse(board, ply=0)
    assert pos.is_critical is True


def test_static_analyzer_complexity_is_in_range() -> None:
    pos = StaticAnalyzer().analyse(chess.Board(), ply=0)
    assert pos.complexity is not None
    assert 0.0 <= pos.complexity.composite <= 1.0


def test_static_analyzer_deterministic() -> None:
    a = StaticAnalyzer()
    board = chess.Board()
    one = a.analyse(board, ply=0)
    two = a.analyse(board, ply=0)
    assert one.model_dump() == two.model_dump()
