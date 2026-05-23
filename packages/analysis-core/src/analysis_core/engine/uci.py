"""Thin UCI wrapper that pins deterministic Stockfish settings.

The pinned settings are taken from research §3 of feature 001:
depth 18, Threads=1 (deterministic), Hash=256MB, MultiPV=5, UseNNUE=true.
A `LockedUciOptions` instance is immutable after construction; the
`Engine` wrapper rejects post-init mutations so a run cannot drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

DEFAULT_DEPTH: Final[int] = 18
DEFAULT_THREADS: Final[int] = 1
DEFAULT_HASH_MB: Final[int] = 256
DEFAULT_MULTIPV: Final[int] = 5
DEFAULT_USE_NNUE: Final[bool] = True


@dataclass(frozen=True, slots=True)
class LockedUciOptions:
    """Immutable bundle of UCI options pinned for determinism."""

    depth: int = DEFAULT_DEPTH
    threads: int = DEFAULT_THREADS
    hash_mb: int = DEFAULT_HASH_MB
    multipv: int = DEFAULT_MULTIPV
    use_nnue: bool = DEFAULT_USE_NNUE

    def as_uci_dict(self) -> dict[str, str | int | bool]:
        return {
            "Threads": self.threads,
            "Hash": self.hash_mb,
            "MultiPV": self.multipv,
            "UseNNUE": self.use_nnue,
        }

    def __post_init__(self) -> None:
        if self.depth < 1:
            raise ValueError(f"depth must be >= 1; got {self.depth}")
        if self.threads != 1:
            raise ValueError(f"threads must equal 1 for determinism; got {self.threads}")
        if self.hash_mb < 16:
            raise ValueError(f"hash_mb must be >= 16; got {self.hash_mb}")
        if self.multipv < 1:
            raise ValueError(f"multipv must be >= 1; got {self.multipv}")
