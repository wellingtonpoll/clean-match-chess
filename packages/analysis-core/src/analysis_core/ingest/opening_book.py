"""Polyglot opening-book lookup (Principle 6).

Wraps `chess.polyglot` to identify "book" plies that the scoring layer
discounts. The book file's SHA256 is recorded in the reproducibility
manifest so the discount is replayable.

MVP-deferred: bundling the canonical Lichess Masters book (>=2400 Elo,
depth 20 plies). Until then, `default_book_path()` returns the path
the build will populate; callers MUST handle FileNotFoundError.
"""

from __future__ import annotations

import hashlib
from contextlib import suppress
from pathlib import Path
from typing import Final

import chess
import chess.polyglot

DEFAULT_BOOK_RELATIVE: Final[Path] = Path(
    "packages/analysis-core/data/books/lichess-masters-2400-d20.bin"
)


def default_book_path() -> Path:
    """Repo-root-relative default path to the canonical Polyglot book."""
    return Path(__file__).resolve().parents[5] / DEFAULT_BOOK_RELATIVE


def sha256_of(book_path: Path) -> str:
    h = hashlib.sha256()
    with book_path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class OpeningBook:
    """In-memory Polyglot book reader."""

    def __init__(self, book_path: Path) -> None:
        if not book_path.is_file():
            raise FileNotFoundError(
                f"opening book not found at {book_path}; bundle the canonical book before audit"
            )
        self._path = book_path
        self._sha256 = sha256_of(book_path)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def sha256(self) -> str:
        return self._sha256

    def is_book_ply(self, board: chess.Board) -> bool:
        """True iff the current position has any entry in the book."""
        with chess.polyglot.open_reader(str(self._path)) as reader, suppress(IndexError):
            for _ in reader.find_all(board):
                return True
        return False
