"""Lexical audit (T081, SC-008)."""

from __future__ import annotations

import pytest
from report_engine.lexical_audit import (
    LexicalAuditError,
    audit_text,
    load_forbidden_terms,
)


def test_load_forbidden_terms_en() -> None:
    terms = load_forbidden_terms("en")
    assert len(terms) >= 12
    assert any(t.term == "cheater" for t in terms)


def test_clean_text_returns_no_findings() -> None:
    findings = audit_text("Probabilistic forensic assessment. Risk: LOW.")
    assert findings == []


def test_word_boundary_match_against_forbidden_term() -> None:
    findings = audit_text("This player is a cheater.")
    assert any(f.term == "cheater" for f in findings)


def test_substring_match_against_forbidden_phrase() -> None:
    findings = audit_text("system confirmed cheating in this game")
    assert any(f.term == "confirmed cheating" for f in findings)


def test_portuguese_terms_detected() -> None:
    findings = audit_text("o jogador foi acusado de trapaça neste torneio")
    assert any(f.language == "pt" and f.term == "trapaça" for f in findings)


def test_audit_error_carries_findings() -> None:
    err = LexicalAuditError(audit_text("cheater"))
    assert err.findings
    assert "cheater" in str(err)


def test_unknown_language_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_forbidden_terms("does-not-exist")
