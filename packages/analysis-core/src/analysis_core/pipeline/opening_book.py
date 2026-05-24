"""Polyglot opening-book wrapper for the analysis pipeline (T005, FR-009).

Thin wrapper around `chess.polyglot.MemoryMappedReader`. A position is
considered "in book" iff the reader returns at least one entry with
`weight > 0` for that position. This module owns the canonical default
path for the bundled book under `packages/analysis-core/data/`.

The lookup is mmap-based and cheap, but `OpeningBook.load()` holds the
reader open for the lifetime of the audit so per-ply lookups do not
re-open the file. Use as:

    book = OpeningBook.load(OpeningBook.default_path())
    for board in boards:
        if book.contains(board):
            ...

For tests that want to disable book lookup entirely, pass an empty path
sentinel (``""``) to the consumer or instantiate ``OpeningBook.empty()``.
"""

from __future__ import annotations

import hashlib
from contextlib import suppress
from pathlib import Path
from typing import Final

import chess
import chess.polyglot

DEFAULT_BOOK_RELATIVE: Final[Path] = Path("packages/analysis-core/data/opening_book.bin")


class OpeningBook:
    """Polyglot book wrapper with cached sha256 and a no-op fallback."""

    def __init__(self, path: Path, *, _empty: bool = False) -> None:
        self._path = path
        self._empty = _empty
        if _empty:
            self._sha256 = "0" * 64
            self._reader: chess.polyglot.MemoryMappedReader | None = None
            return
        if not path.is_file():
            raise FileNotFoundError(
                f"opening book not found at {path}; bundle the canonical book before audit"
            )
        self._sha256 = _sha256_of(path)
        self._reader = chess.polyglot.MemoryMappedReader(str(path))

    # ── constructors ──────────────────────────────────────────────────

    @classmethod
    def load(cls, path: Path | str) -> OpeningBook:
        """Open a polyglot book from `path` and cache its sha256."""
        return cls(Path(path))

    @classmethod
    def empty(cls) -> OpeningBook:
        """Return a sentinel book that marks no position as in-book."""
        return cls(Path(), _empty=True)

    @staticmethod
    def default_path() -> Path:
        """Absolute path to the bundled book under `packages/analysis-core/data/`."""
        # __file__ is at packages/analysis-core/src/analysis_core/pipeline/opening_book.py
        # parents[5] = repo root.
        return Path(__file__).resolve().parents[5] / DEFAULT_BOOK_RELATIVE

    # ── queries ───────────────────────────────────────────────────────

    def contains(self, board: chess.Board) -> bool:
        """True iff the book has any entry for `board` with weight > 0."""
        if self._empty or self._reader is None:
            return False
        with suppress(IndexError, KeyError):
            for entry in self._reader.find_all(board):
                if entry.weight > 0:
                    return True
        return False

    def sha256(self) -> str:
        """Stable sha256 of the underlying file (or zeros for empty book)."""
        return self._sha256

    @property
    def path(self) -> Path:
        return self._path

    @property
    def is_empty(self) -> bool:
        return self._empty

    def close(self) -> None:
        if self._reader is not None:
            self._reader.close()
            self._reader = None

    def __enter__(self) -> OpeningBook:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


__all__ = ["OpeningBook"]
