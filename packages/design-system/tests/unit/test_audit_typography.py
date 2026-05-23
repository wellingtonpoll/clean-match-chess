"""Typography audit static-CSS scan (T035)."""

from __future__ import annotations

from pathlib import Path

from design_system.audits.report import AuditStatus
from design_system.audits.typography import (
    REQUIRED_TYPOGRAPHY_TOKENS,
    audit_generated_css,
)
from design_system.tokens.compile_weasyprint import DEFAULT_OUTPUT


def test_committed_css_passes_typography_audit() -> None:
    report = audit_generated_css(Path(DEFAULT_OUTPUT))
    assert report.status is AuditStatus.PASS
    assert report.findings == ()


def test_missing_typography_token_rejected(tmp_path: Path) -> None:
    css = tmp_path / "stripped.css"
    css.write_text(":root { /* no typography vars */ }\n")
    report = audit_generated_css(css)
    assert report.status is AuditStatus.FAIL
    missing = {f.expected for f in report.findings}
    expected = {f"typography.{name}" for name in REQUIRED_TYPOGRAPHY_TOKENS}
    assert missing == expected
