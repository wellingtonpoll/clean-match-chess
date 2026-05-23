"""PGN loader throughput benchmark (T094 ingest subset)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from analysis_core.ingest.pgn_loader import load_pgn_path

pytestmark = pytest.mark.benchmark

REPO_ROOT = Path(__file__).resolve().parents[4]
MORPHY = REPO_ROOT / "tests" / "fixtures" / "pgn" / "known-clean" / "morphy-vs-allies-1858.pgn"


@pytest.mark.skipif(
    "CLEANMATCH_BENCH" not in os.environ,
    reason="benchmarks gated by CLEANMATCH_BENCH=1 (CI labelled job)",
)
def test_load_pgn_text_throughput(benchmark) -> None:
    game = benchmark(load_pgn_path, MORPHY)
    assert game.ply_count > 0
