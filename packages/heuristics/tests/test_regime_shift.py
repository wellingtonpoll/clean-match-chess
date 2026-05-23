"""Segmentation + regime-shift signal (T040)."""

from __future__ import annotations

import chess
from analysis_core.engine.analysis import StaticAnalyzer
from analysis_core.pipeline.segmentation import segment_game
from heuristics.regime_shift import regime_shift_score, signal_version
from shared_types.signal import Phase


def _positions_from_fens(fens: list[str]) -> tuple:
    a = StaticAnalyzer()
    return tuple(a.analyse(chess.Board(fen), ply=i) for i, fen in enumerate(fens))


def test_segment_game_empty_returns_empty() -> None:
    assert segment_game(()) == ()


def test_segment_game_short_returns_opening_only() -> None:
    short = _positions_from_fens([chess.STARTING_FEN] * 5)
    segs = segment_game(short)
    assert segs[0].phase is Phase.OPENING
    assert segs[0].ply_range == (0, 5)


def test_segment_game_endgame_phase_when_few_pieces() -> None:
    endgame_fen = "8/8/8/4k3/8/4K3/8/8 w - - 0 50"
    positions = _positions_from_fens([chess.STARTING_FEN] * 20 + [endgame_fen] * 5)
    phases = {s.phase for s in segment_game(positions)}
    assert Phase.ENDGAME in phases


def test_regime_shift_signal_version() -> None:
    v = signal_version()
    assert v.name == "regime-shift"
    assert v.version == "0.1.0"


def test_regime_shift_zero_when_one_segment() -> None:
    short = _positions_from_fens([chess.STARTING_FEN] * 5)
    segs = segment_game(short)
    assert regime_shift_score(segs).mean == 0.0


def test_regime_shift_in_unit_interval() -> None:
    positions = _positions_from_fens([chess.STARTING_FEN] * 30)
    segs = segment_game(positions)
    score = regime_shift_score(segs)
    assert 0.0 <= score.mean <= 1.0
