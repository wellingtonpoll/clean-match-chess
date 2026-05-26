"""Tests for `analysis_core.engine.stockfish_pool` (feature 011 Phase 2).

Real-engine tests skip cleanly when `cleanmatch-stockfish:sf16` is not
available locally (mirrors the feature 008 pattern). Pure unit tests
on `PoolConfig` validation + `EnginePool` construction run anywhere.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator

import chess
import pytest
from analysis_core.engine.stockfish_pool import (
    EnginePool,
    PoolConfig,
    PooledAnalyzer,
    StockfishPool,
)

# ── Pure unit tests (no engine) ────────────────────────────────────────


class TestPoolConfigValidation:
    def test_rejects_zero_workers(self) -> None:
        with pytest.raises(ValueError, match="workers must be >= 1"):
            PoolConfig(binary_path="/usr/bin/stockfish", workers=0, options={})  # type: ignore[arg-type]

    def test_rejects_empty_binary_path(self) -> None:
        with pytest.raises(ValueError, match="binary_path must be set"):
            PoolConfig(binary_path="", workers=2, options={})  # type: ignore[arg-type]


class TestEnginePoolConstruction:
    def test_rejects_zero_pool_size(self) -> None:
        with pytest.raises(ValueError, match="pool_size must be >= 1"):
            EnginePool(pool_size=0, command="/usr/bin/stockfish")

    def test_construct_does_not_spawn(self) -> None:
        # Lazy: construction alone should not invoke any subprocess.
        pool = EnginePool(pool_size=4, command="this-binary-does-not-exist-zzz")
        assert pool.pool_size == 4
        assert not pool.closed

    def test_context_manager_close_idempotent(self) -> None:
        pool = EnginePool(pool_size=2, command="this-binary-does-not-exist-zzz")
        pool.close()
        pool.close()  # second close is a no-op
        assert pool.closed


class TestLegacyStubStillImports:
    def test_stockfish_pool_construct_close(self) -> None:
        cfg = PoolConfig(binary_path="/usr/bin/stockfish", workers=2, options={})  # type: ignore[arg-type]
        with StockfishPool(cfg) as pool:
            assert pool.config is cfg
            assert not pool.closed
        assert pool.closed


# ── Real-engine tests (skip when SF16 unavailable) ─────────────────────


def _sf16_available() -> bool:
    """Return True iff cleanmatch-stockfish:sf16 image exists locally."""
    if shutil.which("podman") is None and shutil.which("docker") is None:
        return False
    binary = shutil.which("podman") or shutil.which("docker")
    assert binary is not None
    try:
        result = subprocess.run(  # noqa: S603 — trusted argv from shutil.which
            [binary, "images", "-q", "cleanmatch-stockfish:sf16"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        return False
    return bool(result.stdout.strip())


_SF16 = pytest.mark.skipif(
    not _sf16_available(),
    reason=(
        "cleanmatch-stockfish:sf16 image not available locally — skipping real-engine pool tests"
    ),
)

_SF_CMD = ["podman", "run", "--rm", "-i", "cleanmatch-stockfish:sf16"]


@pytest.fixture
def pool() -> Iterator[EnginePool]:
    p = EnginePool(pool_size=2, command=_SF_CMD)
    try:
        yield p
    finally:
        p.close()


@_SF16
class TestPoolSequentialAudits:
    def test_single_acquire_returns_pooled_analyzer(self, pool: EnginePool) -> None:
        with pool.worker(depth=8, multipv=3) as analyzer:
            assert isinstance(analyzer, PooledAnalyzer)
            pos = analyzer.analyse(chess.Board(), ply=0)
            assert pos.fen == chess.Board().fen()
            assert len(pos.top_moves) > 0

    def test_three_sequential_audits_reuse_worker(self, pool: EnginePool) -> None:
        # First acquire spawns a worker, subsequent acquires reuse it.
        board = chess.Board()
        for ply in range(3):
            with pool.worker(depth=8, multipv=3) as analyzer:
                pos = analyzer.analyse(board, ply=ply)
                assert pos.top_moves
            # Confirm pool only spawned 1 worker total.
        assert pool._spawned == 1

    def test_pool_size_caps_concurrent_workers(self, pool: EnginePool) -> None:
        """Pool size = 2. Acquire 2 workers; the 3rd would block."""
        a1 = pool.worker(depth=8, multipv=3).__enter__()
        a2 = pool.worker(depth=8, multipv=3).__enter__()
        try:
            assert pool._spawned == 2
        finally:
            a1.__exit__(None, None, None)
            a2.__exit__(None, None, None)


@_SF16
class TestPoolReuse:
    def test_same_position_twice_same_top_move(self, pool: EnginePool) -> None:
        """Pool reuse preserves engine state: same FEN audited twice via the
        pool produces the same top-1 move. The exact eval may drift ±a few cp
        across runs (Stockfish has low-level search non-determinism at low
        depths from thread scheduling and TT carryover), but the top move at
        depth >= 10 is stable for non-tactical positions."""
        board = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
        results = []
        for _ in range(2):
            with pool.worker(depth=10, multipv=3) as analyzer:
                pos = analyzer.analyse(board, ply=1)
                results.append((pos.top_moves[0].uci, pos.top_moves[0].eval_cp))
        # Top move must match across runs; eval allowed to drift within ±20 cp.
        assert results[0][0] == results[1][0]
        assert abs(results[0][1] - results[1][1]) <= 20
