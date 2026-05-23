"""Timing-analysis signal (T043)."""

from __future__ import annotations

import chess
from analysis_core.engine.analysis import StaticAnalyzer
from heuristics.timing_analysis import signal_version, timing_anomaly
from shared_types.game import Move, MoveClassification, PlayerColor


def test_signal_version() -> None:
    assert signal_version().name == "timing-analysis"


def test_silent_without_timing_data() -> None:
    a = StaticAnalyzer()
    positions = tuple(a.analyse(chess.Board(), ply=i) for i in range(5))
    moves = tuple(
        Move(
            ply=i,
            san=p.top_moves[0].san,
            uci=p.top_moves[0].uci,
            played_by=PlayerColor.WHITE,
            time_spent_ms=None,
            eval_delta_cp=0,
            classification=MoveClassification.GOOD,
        )
        for i, p in enumerate(positions)
    )
    agg = timing_anomaly(positions, moves)
    assert agg.samples == 0
    assert agg.mean == 0.0
