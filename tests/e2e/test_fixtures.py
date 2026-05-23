"""Fixture-integrity test (T035).

Validates every PGN fixture parses, every game is standard variant, and
every forbidden-terms file is well-formed TSV with a version header.
"""

from __future__ import annotations

import io
from pathlib import Path

import chess.pgn
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures"


def _pgn_files() -> list[Path]:
    out: list[Path] = []
    for sub in ("known-clean", "known-suspect"):
        out.extend(sorted((FIXTURE_ROOT / "pgn" / sub).glob("*.pgn")))
    return out


@pytest.mark.parametrize("pgn_path", _pgn_files(), ids=lambda p: p.name)
def test_pgn_parses_and_is_standard(pgn_path: Path) -> None:
    text = pgn_path.read_text()
    game = chess.pgn.read_game(io.StringIO(text))
    assert game is not None, f"{pgn_path.name} did not parse"
    variant = game.headers.get("Variant", "Standard")
    assert variant.lower() in {"standard", ""}, f"{pgn_path.name} has non-standard variant"

    plies = sum(1 for _ in game.mainline_moves())
    assert plies > 0, f"{pgn_path.name} has zero plies"


def test_known_clean_has_at_least_two_games() -> None:
    files = sorted((FIXTURE_ROOT / "pgn" / "known-clean").glob("*.pgn"))
    assert len(files) >= 2


def test_known_suspect_has_at_least_two_games() -> None:
    files = sorted((FIXTURE_ROOT / "pgn" / "known-suspect").glob("*.pgn"))
    assert len(files) >= 2


def test_known_suspect_includes_selective_assistance() -> None:
    files = {p.name for p in (FIXTURE_ROOT / "pgn" / "known-suspect").glob("*.pgn")}
    assert any("selective" in name for name in files), (
        "SC-002 v1.0.0 requires >=50% selective-assistance examples in the assisted set"
    )


@pytest.mark.parametrize("lang", ["en", "pt"])
def test_forbidden_terms_file_is_well_formed(lang: str) -> None:
    path = FIXTURE_ROOT / "forbidden-terms" / f"{lang}.txt"
    assert path.is_file(), f"missing forbidden-terms/{lang}.txt"

    lines = path.read_text().splitlines()
    assert lines, f"{path} is empty"
    assert lines[0].startswith("# version:"), f"{path} first line must be '# version: <semver>'"

    rows = [line for line in lines if line.strip() and not line.startswith("#")]
    assert rows, f"{path} has no term rows"

    valid_categories = {"accusation", "verdict", "slur"}
    valid_modes = {"word_boundary", "substring"}
    for line_no, row in enumerate(rows, start=1):
        parts = row.split("\t")
        assert len(parts) == 3, f"{path} line {line_no}: expected 3 TSV columns, got {len(parts)}"
        term, category, mode = parts
        assert term.strip(), f"{path} line {line_no}: empty term"
        assert category in valid_categories, f"{path} line {line_no}: unknown category {category!r}"
        assert mode in valid_modes, f"{path} line {line_no}: unknown match_mode {mode!r}"


def test_forbidden_terms_en_pt_have_same_row_count() -> None:
    def _count(path: Path) -> int:
        return sum(
            1 for line in path.read_text().splitlines() if line.strip() and not line.startswith("#")
        )

    en = _count(FIXTURE_ROOT / "forbidden-terms" / "en.txt")
    pt = _count(FIXTURE_ROOT / "forbidden-terms" / "pt.txt")
    assert en == pt, f"forbidden-terms en/pt parallelism broken: en={en} pt={pt}"
