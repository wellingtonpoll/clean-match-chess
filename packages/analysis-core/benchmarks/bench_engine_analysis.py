"""Engine-analysis perf benchmark (T094).

Constitution Principle IV budget: <= 2.0 s wall-clock per ply at depth 18
on the reference machine (8-core x86_64, Stockfish 16, single-threaded
per game). This bench exercises the StaticAnalyzer (production default
until real Stockfish wiring lands) and provides the harness real
Stockfish can plug into via CLEANMATCH_BENCH_STOCKFISH=1.

Run with:
    uv run pytest packages/analysis-core/benchmarks -m benchmark
"""

from __future__ import annotations

import os

import chess
import pytest
from analysis_core.engine.analysis import StaticAnalyzer

pytestmark = pytest.mark.benchmark


@pytest.mark.skipif(
    "CLEANMATCH_BENCH" not in os.environ,
    reason="benchmarks gated by CLEANMATCH_BENCH=1 (CI labelled job)",
)
def test_static_analyzer_ply_throughput(benchmark) -> None:
    analyzer = StaticAnalyzer()
    board = chess.Board()
    result = benchmark(analyzer.analyse, board, 0)
    assert result is not None
    # StaticAnalyzer has no engine wait; should run in microseconds.
    assert benchmark.stats["mean"] < 0.01
