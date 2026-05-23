"""Multiprocessing pool of Stockfish workers (skeleton).

Phase 2 ships only the configuration + shutdown surface; the actual
worker process wiring lands with US1 (Phase 3) when the analysis
pipeline is built.
"""

from __future__ import annotations

from dataclasses import dataclass

from analysis_core.engine.uci import LockedUciOptions


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


class StockfishPool:
    """Placeholder for the Phase-3 worker pool.

    Construct + `close()` semantics are stable; analyse() will be
    implemented in US1 against the real python-chess UCI driver.
    """

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
