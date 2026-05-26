"""PGN loader contract tests (T036).

Covers: valid PGN parses, malformed input rejected with PgnValidationError,
non-standard variant rejected, scoring-eligibility gate, canonical hash
stability.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from analysis_core.ingest.pgn_loader import (
    PLY_MIN_FOR_SCORING,
    PgnValidationError,
    is_eligible_for_scoring,
    load_pgn_path,
    load_pgn_text,
)
from shared_types.game import PlayerColor, Result, TimeControlCategory

REPO_ROOT = Path(__file__).resolve().parents[3]
CLEAN_DIR = REPO_ROOT / "tests" / "fixtures" / "pgn" / "known-clean"
MORPHY = CLEAN_DIR / "morphy-vs-allies-1858.pgn"
ANDERSSEN = CLEAN_DIR / "anderssen-vs-kieseritzky-1851.pgn"


def test_load_known_clean_morphy_parses() -> None:
    game = load_pgn_path(MORPHY)
    assert game.ply_count > 30
    assert game.result is Result.WHITE_WINS
    assert game.players[0].color is PlayerColor.WHITE
    assert game.players[1].color is PlayerColor.BLACK
    assert game.eco == "C41"


def test_load_known_clean_anderssen_parses() -> None:
    game = load_pgn_path(ANDERSSEN)
    assert game.ply_count >= 40
    assert game.eco == "C33"


def test_empty_pgn_rejected() -> None:
    with pytest.raises(PgnValidationError, match="empty"):
        load_pgn_text("")


def test_malformed_pgn_rejected() -> None:
    with pytest.raises(PgnValidationError):
        load_pgn_text("not actually a pgn document")


def test_nonstandard_variant_rejected() -> None:
    pgn = '[Event "?"]\n[White "a"]\n[Black "b"]\n[Variant "Chess960"]\n[Result "*"]\n\n1. e4 *\n'
    with pytest.raises(PgnValidationError, match="variant"):
        load_pgn_text(pgn)


def test_pgn_sha256_is_deterministic() -> None:
    a = load_pgn_path(MORPHY)
    b = load_pgn_path(MORPHY)
    assert a.pgn_sha256 == b.pgn_sha256


def test_missing_path_rejected(tmp_path: Path) -> None:
    with pytest.raises(PgnValidationError, match="not found"):
        load_pgn_path(tmp_path / "does-not-exist.pgn")


def test_scoring_eligibility_threshold() -> None:
    pgn = '[Event "?"]\n[White "a"]\n[Black "b"]\n[Result "*"]\n\n1. e4 e5 *\n'
    game = load_pgn_text(pgn)
    assert game.ply_count < PLY_MIN_FOR_SCORING
    assert is_eligible_for_scoring(game) is False


def test_time_control_parsed() -> None:
    pgn = (
        '[Event "?"]\n[White "a"]\n[Black "b"]\n[Result "*"]\n[TimeControl "180+2"]\n\n1. e4 e5 *\n'
    )
    game = load_pgn_text(pgn)
    assert game.time_control.base_seconds == 180
    assert game.time_control.increment_seconds == 2
    assert game.time_control.category is TimeControlCategory.BLITZ


# ─── Per-move clock extraction (feature 011, FR-001 / FR-002) ─────────


def test_no_clock_annotations_leaves_time_spent_none() -> None:
    pgn = (
        '[Event "?"]\n[White "a"]\n[Black "b"]\n[Result "*"]\n[TimeControl "600+0"]\n\n'
        "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *\n"
    )
    game = load_pgn_text(pgn)
    assert all(m.time_spent_ms is None for m in game.moves)


def test_clock_annotations_populate_time_spent_no_increment() -> None:
    """10-min game, no increment. First move uses 5 s; clock 600 → 595."""
    pgn = (
        '[Event "?"]\n[White "a"]\n[Black "b"]\n[Result "*"]\n[TimeControl "600+0"]\n\n'
        "1. e4 {[%clk 0:09:55]} e5 {[%clk 0:09:58]} "
        "2. Nf3 {[%clk 0:09:50]} Nc6 {[%clk 0:09:54]} *\n"
    )
    game = load_pgn_text(pgn)
    times = [m.time_spent_ms for m in game.moves]
    # ply 0 = white e4, prior=600000, current=595000, inc=0 → 5000 ms
    assert times[0] == 5000
    # ply 1 = black e5, prior=600000, current=598000, inc=0 → 2000 ms
    assert times[1] == 2000
    # ply 2 = white Nf3, prior=595000, current=590000 → 5000 ms
    assert times[2] == 5000
    # ply 3 = black Nc6, prior=598000, current=594000 → 4000 ms
    assert times[3] == 4000


def test_clock_annotations_with_increment() -> None:
    """600+5: clock displayed AFTER increment credit. Used 8 s for first move."""
    pgn = (
        '[Event "?"]\n[White "a"]\n[Black "b"]\n[Result "*"]\n[TimeControl "600+5"]\n\n'
        "1. e4 {[%clk 0:09:57]} e5 {[%clk 0:09:57]} *\n"
    )
    game = load_pgn_text(pgn)
    # ply 0: prior=600_000, current=597_000, inc=5_000 → 8_000 ms thinking.
    assert game.moves[0].time_spent_ms == 8000
    # ply 1: same math for black.
    assert game.moves[1].time_spent_ms == 8000


def test_clock_clamps_to_zero_on_negative_delta() -> None:
    """If clock somehow INCREASES across moves (corrupted PGN), clamp to 0."""
    pgn = (
        '[Event "?"]\n[White "a"]\n[Black "b"]\n[Result "*"]\n[TimeControl "600+0"]\n\n'
        "1. e4 {[%clk 0:11:00]} *\n"  # clock magically gained 60s
    )
    game = load_pgn_text(pgn)
    assert game.moves[0].time_spent_ms == 0


def test_lichess_eval_annotation_doesnt_block_clock() -> None:
    """Lichess sometimes adds [%eval] before [%clk]; we must still parse the clock."""
    pgn = (
        '[Event "?"]\n[White "a"]\n[Black "b"]\n[Result "*"]\n[TimeControl "180+1"]\n\n'
        "1. e4 {[%eval 0.23] [%clk 0:02:58]} *\n"
    )
    game = load_pgn_text(pgn)
    # prior 180000 → current 178000, inc 1000 → 3000 ms
    assert game.moves[0].time_spent_ms == 3000
