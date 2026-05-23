"""Dynamic motion audit harness (T066)."""

from __future__ import annotations

from design_system.audits.motion import audit_web
from design_system.audits.report import AuditStatus


def test_audit_web_skips_without_env_gate(monkeypatch) -> None:
    monkeypatch.delenv("CLEANMATCH_WEB_AUDIT", raising=False)
    report = audit_web("tests/fixtures/web/synthetic.html")
    assert report.status is AuditStatus.PASS
    assert any(f.rule == "web_audit_skipped" for f in report.findings)


def test_audit_web_deferred_with_env_gate(monkeypatch) -> None:
    monkeypatch.setenv("CLEANMATCH_WEB_AUDIT", "1")
    report = audit_web("tests/fixtures/web/synthetic.html")
    assert report.status is AuditStatus.PASS
    assert any(f.rule == "web_audit_deferred" for f in report.findings)
