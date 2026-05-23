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
