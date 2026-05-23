"""OpeningBook contract tests (Polyglot lookup deferred to bundled book)."""

from __future__ import annotations

from pathlib import Path

import pytest
from analysis_core.ingest.opening_book import OpeningBook, default_book_path, sha256_of


def test_default_book_path_relative_to_repo() -> None:
    path = default_book_path()
    assert path.name == "lichess-masters-2400-d20.bin"
    assert "data/books" in str(path)


def test_missing_book_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        OpeningBook(tmp_path / "does-not-exist.bin")


def test_sha256_of_known_bytes(tmp_path: Path) -> None:
    target = tmp_path / "fake-book.bin"
    target.write_bytes(b"hello, polyglot")
    digest = sha256_of(target)
    # SHA-256 of the literal bytes above.
    assert digest == "4d91521ff0d3739a8074773170618be6b2a96b3c82e8a76674e3aeff7c2a3e91"
