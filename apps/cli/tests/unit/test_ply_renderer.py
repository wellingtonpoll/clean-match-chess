"""Per-ply renderer (T071)."""

from __future__ import annotations

import chess
import pytest
from analysis_core.engine.analysis import StaticAnalyzer
from analysis_core.ingest.pgn_loader import load_pgn_text
from cleanmatch_cli.output.ply_renderer import PlyInvariantReport, render_ply
from shared_types.game import MoveClassification


@pytest.fixture
def small_game():
    pgn = (
        '[Event "?"]\n[White "alice"]\n[Black "bob"]\n[Result "1-0"]\n'
        '[TimeControl "600"]\n\n1. e4 e5 2. Nf3 Nc6 *\n'
    )
    return load_pgn_text(pgn)


def test_render_ply_emits_move_position_and_top_moves(small_game) -> None:
    a = StaticAnalyzer()
    board = chess.Board()
    move = small_game.moves[0]
    pos = a.analyse(board, ply=0)
    lines, invariant = render_ply(0, move, pos)
    joined = "\n".join(lines)
    assert move.san in joined
    assert "Position complexity" in joined
    assert "Engine top moves" in joined
    assert isinstance(invariant, PlyInvariantReport)


def test_render_ply_emits_principle_note_for_critical_position(small_game) -> None:
    a = StaticAnalyzer()
    check_fen = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
    board = chess.Board(check_fen)
    pos = a.analyse(board, ply=2)
    move = (
        small_game.moves[0]._replace_classification(MoveClassification.GOOD)
        if hasattr(small_game.moves[0], "_replace_classification")
        else small_game.moves[0]
    )
    lines, invariant = render_ply(2, move, pos)
    joined = "\n".join(lines)
    assert "Principle" in joined
    assert invariant.principle_count >= 1


def test_render_ply_never_uses_accusatory_words(small_game) -> None:
    a = StaticAnalyzer()
    pos = a.analyse(chess.Board(), ply=0)
    lines, _ = render_ply(0, small_game.moves[0], pos)
    joined = "\n".join(lines).lower()
    for forbidden in ("cheater", "cheating", "guilty", "fraud", "trapaceiro"):
        assert forbidden not in joined
