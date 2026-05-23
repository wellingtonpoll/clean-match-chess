"""Lexicon + forbidden-terms loaders (T012 + T013)."""

from __future__ import annotations

from pathlib import Path

import pytest
from design_system.lexicon.lookup import (
    ForbiddenCategory,
    LexiconEntry,
    LexiconValidationError,
    MatchMode,
    forbidden_alternatives_resolve,
    load_forbidden_terms,
)


def test_load_forbidden_terms_en() -> None:
    ft = load_forbidden_terms("en")
    assert ft.language == "en"
    assert len(ft.terms) >= 12
    assert any(t.term == "cheater" for t in ft.terms)


def test_load_forbidden_terms_pt() -> None:
    ft = load_forbidden_terms("pt")
    assert ft.language == "pt"
    assert any(t.term == "trapaceiro" for t in ft.terms)


def test_load_forbidden_terms_carries_version() -> None:
    ft = load_forbidden_terms("en")
    assert ft.version == "1.0.0"


def test_load_forbidden_terms_unknown_language_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_forbidden_terms("xx")


def test_malformed_tsv_row_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.txt"
    bad.write_text("# version: 0.1.0\ncheater\tonly two columns\n")
    with pytest.raises(LexiconValidationError):
        load_forbidden_terms("bad", root=tmp_path)


def test_unknown_category_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.txt"
    bad.write_text("# version: 0.1.0\ncheater\tbogus\tword_boundary\n")
    with pytest.raises(LexiconValidationError):
        load_forbidden_terms("bad", root=tmp_path)


def test_forbidden_alternatives_resolve_matches_universe() -> None:
    ft = load_forbidden_terms("en")
    entry = LexiconEntry(
        term="Behavioral Signal",
        definition="A computed behavioural metric.",
        context="narrative",
        alternatives_forbidden=("cheater",),
    )
    assert forbidden_alternatives_resolve(entry, ft) is True


def test_forbidden_alternatives_resolve_rejects_missing() -> None:
    ft = load_forbidden_terms("en")
    entry = LexiconEntry(
        term="Risk Window",
        definition="A flagged region of the game.",
        context="narrative",
        alternatives_forbidden=("does-not-exist",),
    )
    assert forbidden_alternatives_resolve(entry, ft) is False


def test_categories_and_modes_enum_values() -> None:
    ft = load_forbidden_terms("en")
    for t in ft.terms:
        assert t.category in ForbiddenCategory
        assert t.match_mode in MatchMode
