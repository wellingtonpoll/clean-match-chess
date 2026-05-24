"""OpeningBook (pipeline) contract tests (T011).

Verifies the new `analysis_core.pipeline.opening_book.OpeningBook`
wrapper:
  (a) `contains()` is True for the starting position (the bundled book
      always has theory for the start of the game).
  (b) `contains()` is False for an obviously non-book position reached
      by pushing 10 nonsense moves.
  (c) `sha256()` is stable across two independent `load()` calls.
"""

from __future__ import annotations

from pathlib import Path

import chess
import pytest
from analysis_core.pipeline.opening_book import OpeningBook


def test_contains_returns_true_for_starting_position() -> None:
    book = OpeningBook.load(OpeningBook.default_path())
    try:
        assert book.contains(chess.Board()) is True
    finally:
        book.close()


def test_contains_returns_false_for_obviously_non_book_position() -> None:
    book = OpeningBook.load(OpeningBook.default_path())
    try:
        board = chess.Board()
        # 10 plies of nonsense rook-pawn shuffling — guaranteed not in any
        # opening book.
        for uci in (
            "a2a3", "a7a6", "a3a4", "a6a5", "h2h3",
            "h7h6", "h3h4", "h6h5", "b2b3", "b7b6",
        ):
            board.push(chess.Move.from_uci(uci))
        assert book.contains(board) is False
    finally:
        book.close()


def test_sha256_stable_across_loads() -> None:
    b1 = OpeningBook.load(OpeningBook.default_path())
    b2 = OpeningBook.load(OpeningBook.default_path())
    try:
        assert b1.sha256() == b2.sha256()
        assert len(b1.sha256()) == 64
    finally:
        b1.close()
        b2.close()


def test_missing_book_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        OpeningBook.load(tmp_path / "does-not-exist.bin")


def test_empty_book_marks_nothing_as_book() -> None:
    book = OpeningBook.empty()
    assert book.is_empty is True
    assert book.contains(chess.Board()) is False
    assert book.sha256() == "0" * 64


def test_default_path_resolves_to_bundled_book() -> None:
    path = OpeningBook.default_path()
    assert path.is_file()
    assert path.name == "opening_book.bin"
    assert "packages/analysis-core/data" in str(path)
