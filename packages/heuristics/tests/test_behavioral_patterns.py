"""Behavioral-patterns signal (T042)."""

from __future__ import annotations

import chess
from analysis_core.engine.analysis import StaticAnalyzer
from heuristics.behavioral_patterns import (
    blunder_suppression,
    precision_burst,
    signal_version,
)
from shared_types.game import Move, MoveClassification, PlayerColor


def test_signal_version() -> None:
    assert signal_version().name == "behavioral-patterns"


def test_precision_burst_with_aligned_moves() -> None:
    a = StaticAnalyzer()
    positions = tuple(a.analyse(chess.Board(), ply=i) for i in range(6))
    aligned = tuple(
        Move(
            ply=i,
            san=p.top_moves[0].san,
            uci=p.top_moves[0].uci,
            played_by=PlayerColor.WHITE,
            eval_delta_cp=0,
            classification=MoveClassification.GOOD,
        )
        for i, p in enumerate(positions)
    )
    agg = precision_burst(positions, aligned)
    assert 0.0 <= agg.mean <= 1.0
    assert agg.samples == 6


def test_blunder_suppression_with_no_complex_positions() -> None:
    a = StaticAnalyzer()
    positions = tuple(a.analyse(chess.Board(), ply=i) for i in range(5))
    agg = blunder_suppression(positions)
    assert agg.samples == 0
