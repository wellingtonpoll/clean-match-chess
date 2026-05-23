"""Tactical-detection signal (T039)."""

from __future__ import annotations

import chess
from analysis_core.engine.analysis import StaticAnalyzer
from heuristics.tactical_detection import signal_version, tactical_density


def _positions(fens: list[str]) -> tuple:
    a = StaticAnalyzer()
    return tuple(a.analyse(chess.Board(fen), ply=i) for i, fen in enumerate(fens))


def test_signal_version() -> None:
    assert signal_version().name == "tactical-detection"


def test_empty_returns_zero() -> None:
    agg = tactical_density(())
    assert agg.samples == 0


def test_critical_positions_lift_density() -> None:
    check_fen = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
    plain = chess.STARTING_FEN
    positions = _positions([plain, check_fen, plain, check_fen])
    agg = tactical_density(positions)
    assert agg.mean > 0.0
