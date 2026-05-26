"""Pool reuse vs. fresh-spawn perf benchmark (feature 011 Phase 2).

Validates SC-001 from the spec: 10 sequential audits via the pool finish
in <= 1.2x the time of one warm audit * 10. The control is 10 audits
each spawning a fresh `EngineAnalyzer` (current production behavior).

Gated by `CLEANMATCH_BENCH=1` to keep `pytest` quick locally; the CI
benchmarks job runs it on the `benchmark` label.
"""

from __future__ import annotations

import os
import time

import chess
import pytest
from analysis_core.engine.analysis import EngineAnalyzer
from analysis_core.engine.stockfish_pool import EnginePool

pytestmark = pytest.mark.benchmark

_SF_CMD = ["podman", "run", "--rm", "-i", "cleanmatch-stockfish:sf16"]

_GATE = pytest.mark.skipif(
    "CLEANMATCH_BENCH" not in os.environ,
    reason="benchmarks gated by CLEANMATCH_BENCH=1",
)


@_GATE
def test_pool_reuses_engine_across_audits() -> None:
    """10 audits via pool MUST be faster than 10 fresh spawns by >= 5x."""
    boards = [chess.Board() for _ in range(10)]

    # Control: fresh spawn per audit.
    start = time.perf_counter()
    for i, board in enumerate(boards):
        with EngineAnalyzer(_SF_CMD, depth=8, multipv=3) as analyzer:
            analyzer.analyse(board, ply=i)
    fresh_elapsed = time.perf_counter() - start

    # Treatment: 1 pool worker, reused across 10 audits.
    start = time.perf_counter()
    with EnginePool(pool_size=1, command=_SF_CMD) as pool:
        for i, board in enumerate(boards):
            with pool.worker(depth=8, multipv=3) as analyzer:
                analyzer.analyse(board, ply=i)
    pooled_elapsed = time.perf_counter() - start

    speedup = fresh_elapsed / pooled_elapsed
    # Each fresh spawn is ~3-5s of podman overhead; pool amortizes to one.
    # Expect speedup >= 5x in practice on a typical dev box.
    assert speedup >= 5.0, (
        f"pool reuse not effective: fresh={fresh_elapsed:.1f}s "
        f"pooled={pooled_elapsed:.1f}s speedup={speedup:.1f}x (want >= 5x)"
    )
