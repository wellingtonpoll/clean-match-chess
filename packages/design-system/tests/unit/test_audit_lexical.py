"""Lexical audit (T040)."""

from __future__ import annotations

from design_system.audits.lexical import audit_text
from design_system.audits.report import AuditStatus


def test_clean_text_passes() -> None:
    report = audit_text("Probabilistic forensic assessment. Risk: LOW.")
    assert report.status is AuditStatus.PASS
    assert report.findings == ()


def test_word_boundary_match() -> None:
    report = audit_text("This player is a cheater.")
    assert report.status is AuditStatus.FAIL
    assert any(f.rule == "forbidden_term" for f in report.findings)


def test_substring_match() -> None:
    report = audit_text("system confirmed cheating today")
    assert report.status is AuditStatus.FAIL
    assert any("confirmed cheating" in f.actual for f in report.findings)


def test_portuguese_term_detected() -> None:
    report = audit_text("o jogador foi acusado de trapaça")
    assert report.status is AuditStatus.FAIL
    pt_findings = [f for f in report.findings if "pt" in f.message]
    assert pt_findings


def test_audit_text_carries_language_in_message() -> None:
    report = audit_text("cheater")
    assert any("en" in f.message for f in report.findings)
