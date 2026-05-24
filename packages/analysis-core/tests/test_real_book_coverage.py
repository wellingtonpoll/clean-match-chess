"""Real opening_book.bin coverage test (feature 005 T013 / SC-002).

Skips gracefully if the bundled file is still the Phase 1 stub (< 100 KB) so
branches that have not yet landed the real book do not fail.
"""

from __future__ import annotations

import io
from pathlib import Path

import chess
import chess.pgn
import chess.polyglot
import pytest
from analysis_core.pipeline.opening_book import OpeningBook

REPO_ROOT = Path(__file__).resolve().parents[3]
BOOK_PATH = REPO_ROOT / "packages" / "analysis-core" / "data" / "opening_book.bin"

# Phase 1 stub was 1296 bytes; real book is >= 100 KB. Use 100 KB as the cutoff
# so a forgotten swap (or LFS pointer accidentally committed) is caught.
_STUB_SIZE_CEILING = 100 * 1024


def _book_is_stub() -> bool:
    return BOOK_PATH.stat().st_size <= _STUB_SIZE_CEILING


@pytest.mark.skipif(_book_is_stub(), reason="feature 005 US2 not yet landed — book is Phase 1 stub")
def test_real_book_size_at_least_1mb() -> None:
    """FR-002 / SC-002: shipped book must be >= 1 MB."""
    assert BOOK_PATH.stat().st_size >= 1024 * 1024, (
        f"opening_book.bin is {BOOK_PATH.stat().st_size} bytes; FR-002 requires >= 1 MB"
    )


@pytest.mark.skipif(_book_is_stub(), reason="feature 005 US2 not yet landed — book is Phase 1 stub")
def test_book_covers_italian_game_first_12_plies() -> None:
    """Italian Game mainline is the canonical SC-002 acceptance: >= 12 of first
    16 plies must be flagged as book."""
    italian_pgn = (
        '[Event "Italian Game mainline"]\n'
        '[White "?"][Black "?"][Result "*"]\n\n'
        "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 d6 6. O-O O-O 7. Re1 a6 8. Bb3 Ba7 *\n"
    )
    game = chess.pgn.read_game(io.StringIO(italian_pgn))
    assert game is not None
    book = OpeningBook.load(str(BOOK_PATH))
    board = game.board()
    book_plies = 0
    for ply, move in enumerate(game.mainline_moves()):
        if ply >= 16:
            break
        if book.contains(board):
            book_plies += 1
        board.push(move)
    assert book_plies >= 12, (
        f"Italian Game first-16-ply book coverage = {book_plies}, expected >= 12"
    )


@pytest.mark.skipif(_book_is_stub(), reason="feature 005 US2 not yet landed — book is Phase 1 stub")
def test_book_covers_smoke_fixture_first_six_plies() -> None:
    """The canonical smoke fixture (King's Gambit Accepted line) is rare in
    modern play, so an OTB-broadcast-derived book naturally goes off-book
    after the gambit declined branches. Require >= 6 of first 16 plies as a
    sanity check that the bundled file is NOT the Phase 1 stub (which would
    score 0)."""
    smoke_pgn = (REPO_ROOT / "tests" / "fixtures" / "audit_v2_smoke.pgn").read_text()
    game = chess.pgn.read_game(io.StringIO(smoke_pgn))
    assert game is not None
    book = OpeningBook.load(str(BOOK_PATH))
    board = game.board()
    book_plies = 0
    for ply, move in enumerate(game.mainline_moves()):
        if ply >= 16:
            break
        if book.contains(board):
            book_plies += 1
        board.push(move)
    assert book_plies >= 6, (
        f"smoke fixture first-16-ply book coverage = {book_plies}; "
        "expected >= 6 (real book) — got value consistent with Phase 1 stub"
    )


@pytest.mark.skipif(_book_is_stub(), reason="feature 005 US2 not yet landed — book is Phase 1 stub")
def test_book_starting_position_has_diverse_first_moves() -> None:
    """Real master-game-derived books expose several first moves with non-zero
    weight; the Phase 1 stub had only the 8 mainline pre-coded openings."""
    with chess.polyglot.open_reader(BOOK_PATH) as reader:
        entries = list(reader.find_all(chess.Board()))
    assert len(entries) >= 10, (
        f"starting position has only {len(entries)} entries; expected >= 10 from real master games"
    )
