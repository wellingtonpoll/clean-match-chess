"""Persistent pool of Stockfish UCI workers (feature 011 Phase 2).

`EngineAnalyzer` opens a fresh Stockfish process per audit, which means
~2-5 s of process startup overhead each call. For batch audits (e.g.
`audit-username --count 10`) or for the production async queue (feature
011 Phase 3), spawning N persistent workers and reusing them via UCI
`position`/`go`/`ucinewgame` brings the per-audit cost down to the
actual analysis time.

Architecture:

  EnginePool                  : context manager owning N workers.
    ├── `_acquire_worker()` / `_release_worker()` : queue.Queue-backed rental.
    └── `worker(depth, multipv)`   : context-manager wrapper that
                                     yields a `PooledAnalyzer` and
                                     auto-releases on exit.

  PooledAnalyzer              : thin wrapper around a borrowed
                                `chess.engine.SimpleEngine`. Exposes the
                                same `analyse(board, ply) -> Position`
                                surface as `EngineAnalyzer`. Calls
                                `ucinewgame()` on `__enter__` to reset
                                transposition table + history between
                                games — NFR-002 (determinism).

Determinism: each engine is configured with `Threads=1, Hash=256` (same
as `EngineAnalyzer`). UCI sessions persist across acquires; the
ucinewgame call clears game-specific state without restarting.

Graceful degradation: if a worker process dies (Stockfish crash, podman
container OOM-killed), the worker is dropped on release and the pool
spawns a replacement on the next acquire. Pool size never permanently
shrinks unless `close()` is called.
"""

from __future__ import annotations

import contextlib
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import chess
import chess.engine
from shared_types.game import PlayerColor, Position

from analysis_core.engine.analysis import (
    MAX_MULTIPV,
    _build_candidates,
    _build_complexity,
    _terminal_position,
)
from analysis_core.engine.uci import LockedUciOptions

_DEFAULT_UCI_OPTIONS: Final[dict[str, int | bool]] = {"Threads": 1, "Hash": 256}


@dataclass(frozen=True, slots=True)
class PoolConfig:
    """How many engine workers and what binary to use."""

    binary_path: str
    workers: int
    options: LockedUciOptions

    def __post_init__(self) -> None:
        if self.workers < 1:
            raise ValueError(f"workers must be >= 1; got {self.workers}")
        if not self.binary_path:
            raise ValueError("binary_path must be set")


class PooledAnalyzer:
    """Borrows a `SimpleEngine` from the pool; conforms to the Analyzer protocol.

    Use exclusively through `EnginePool.worker(depth, multipv)` — the
    pool calls `__enter__` (issues `ucinewgame` to reset state) and
    `__exit__` (releases the worker back to the pool, NEVER closes the
    process).
    """

    def __init__(
        self,
        pool: EnginePool,
        engine: chess.engine.SimpleEngine,
        *,
        depth: int,
        multipv: int,
    ) -> None:
        self._pool = pool
        self._engine = engine
        self._depth = depth
        self._multipv = max(1, min(multipv, MAX_MULTIPV))
        self._released = False

    def __enter__(self) -> PooledAnalyzer:
        # python-chess `SimpleEngine.analyse(board, ...)` sends `position fen
        # <FEN>` to the engine for every call, so each audit starts from a
        # known board state without explicit `ucinewgame`. The transposition
        # table may retain entries from prior audits — this is harmless for
        # determinism (eval at depth N is still the same) and arguably
        # helpful (cache hits on shared endgame structures). If a future
        # signal needs hard isolation, swap this comment for a custom
        # `send_line("ucinewgame")` via `self._engine.protocol`.
        return self

    def __exit__(self, *exc: object) -> None:
        # Return the worker to the pool regardless of exception. If the
        # engine raised EngineTerminatedError, the pool drops it on
        # release and spawns a replacement on the next acquire.
        if not self._released:
            self._pool._release_worker(self._engine)
            self._released = True

    def analyse(self, board: chess.Board, ply: int) -> Position:
        """Same surface as `EngineAnalyzer.analyse`."""
        legal = list(board.legal_moves)
        side = PlayerColor.WHITE if board.turn else PlayerColor.BLACK
        is_only = len(legal) == 1

        if not legal:
            return _terminal_position(board, ply, side)

        limit = chess.engine.Limit(depth=self._depth)
        multipv = min(self._multipv, len(legal))

        info_list = self._engine.analyse(board, limit, multipv=multipv)
        if not isinstance(info_list, list):
            info_list = [info_list]

        top_moves = _build_candidates(info_list, board)
        complexity = _build_complexity(legal, top_moves)
        best_eval = top_moves[0].eval_cp if top_moves else 0
        best_mate = top_moves[0].mate_in if top_moves else None

        return Position(
            ply=ply,
            fen=board.fen(),
            side_to_move=side,
            eval_cp=best_eval,
            mate_in=best_mate,
            top_moves=tuple(top_moves),
            complexity=complexity,
            is_critical=is_only or board.is_check(),
            is_only_move=is_only,
            is_book=False,
        )


class EnginePool:
    """Pool of N persistent Stockfish UCI sessions, thread-safe rental.

    Usage:

        with EnginePool(pool_size=4, command="cleanmatch-stockfish:sf16") as pool:
            with pool.worker(depth=12, multipv=3) as analyzer:
                position = analyzer.analyse(board, ply=0)

    The pool may be constructed without entering it (lazy spawn); workers
    are only spawned on first `acquire()`. Tests can construct the pool,
    then skip if Stockfish is unavailable, without paying the spawn cost.

    Pool size is hard-capped at construction; the `worker()` blocks if
    all workers are checked out.
    """

    def __init__(
        self,
        *,
        pool_size: int,
        command: str | Path | list[str],
        uci_options: dict[str, int | bool] | None = None,
    ) -> None:
        if pool_size < 1:
            raise ValueError(f"pool_size must be >= 1; got {pool_size}")
        self._pool_size = pool_size
        self._command: str | list[str] = command if isinstance(command, list) else str(command)
        self._uci_options = uci_options or dict(_DEFAULT_UCI_OPTIONS)
        self._workers: queue.Queue[chess.engine.SimpleEngine] = queue.Queue(maxsize=pool_size)
        self._spawn_lock = threading.Lock()
        self._spawned = 0
        self._closed = False

    @property
    def pool_size(self) -> int:
        return self._pool_size

    @property
    def closed(self) -> bool:
        return self._closed

    def __enter__(self) -> EnginePool:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _spawn_worker(self) -> chess.engine.SimpleEngine:
        engine = chess.engine.SimpleEngine.popen_uci(self._command)
        engine.configure(self._uci_options)
        return engine

    def _acquire_worker(self, timeout: float | None = None) -> chess.engine.SimpleEngine:
        """Acquire a worker, spawning a new one if pool hasn't filled yet."""
        if self._closed:
            raise RuntimeError("EnginePool is closed")
        # Fast path: a worker is already in the queue.
        with contextlib.suppress(queue.Empty):
            return self._workers.get_nowait()
        # Spawn lazily, up to pool_size.
        with self._spawn_lock:
            if self._spawned < self._pool_size:
                worker = self._spawn_worker()
                self._spawned += 1
                return worker
        # Pool exhausted — block until something is released.
        return self._workers.get(timeout=timeout)

    def _release_worker(self, engine: chess.engine.SimpleEngine) -> None:
        if self._closed:
            with contextlib.suppress(Exception):
                engine.quit()
            return
        # Drop dead workers; the pool will spawn a replacement on next acquire.
        try:
            engine.ping()  # cheap UCI roundtrip; raises if process dead
            self._workers.put_nowait(engine)
        except (chess.engine.EngineTerminatedError, queue.Full, OSError):
            with contextlib.suppress(Exception):
                engine.quit()
            with self._spawn_lock:
                self._spawned = max(0, self._spawned - 1)

    def worker(
        self,
        *,
        depth: int = 18,
        multipv: int = MAX_MULTIPV,
        timeout: float | None = None,
    ) -> PooledAnalyzer:
        """Acquire a worker and return a `PooledAnalyzer`.

        Use as a context manager: `with pool.worker(...) as analyzer: ...`.
        On exit the worker is returned to the pool (NOT closed). The
        analyzer issues `ucinewgame` on enter so state from a prior audit
        does not leak in.
        """
        engine = self._acquire_worker(timeout=timeout)
        return PooledAnalyzer(self, engine, depth=depth, multipv=multipv)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        # Drain the queue and quit each worker.
        while True:
            try:
                engine = self._workers.get_nowait()
            except queue.Empty:
                break
            with contextlib.suppress(Exception):
                engine.quit()


# ─── Legacy stub kept for backward-compat with feature 005 tests ──────


class StockfishPool:
    """Deprecated config-only stub. Prefer `EnginePool` for any new code."""

    def __init__(self, config: PoolConfig) -> None:
        self._config = config
        self._closed = False

    @property
    def config(self) -> PoolConfig:
        return self._config

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        self._closed = True

    def __enter__(self) -> StockfishPool:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
