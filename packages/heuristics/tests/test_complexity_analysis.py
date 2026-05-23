"""Complexity-analysis signal (T038)."""

from __future__ import annotations

import chess
from analysis_core.engine.analysis import StaticAnalyzer
from heuristics.complexity_analysis import complexity_score, signal_version


def _positions(n: int) -> tuple:
    a = StaticAnalyzer()
    return tuple(a.analyse(chess.Board(), ply=i) for i in range(n))


def test_signal_version() -> None:
    assert signal_version().name == "complexity-analysis"


def test_empty_returns_zero() -> None:
    agg = complexity_score(())
    assert agg.samples == 0
    assert agg.mean == 0.0


def test_mean_in_unit_interval() -> None:
    agg = complexity_score(_positions(10))
    assert 0.0 <= agg.mean <= 1.0
    assert agg.samples == 10
