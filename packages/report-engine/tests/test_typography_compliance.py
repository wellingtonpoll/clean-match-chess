"""Typography compliance (T046)."""

from __future__ import annotations

import pytest
from design_system.audits.report import AuditStatus
from design_system.audits.typography import audit_generated_css
from report_engine.styles import get_weasyprint_css_path


@pytest.mark.audit_typography
def test_bundled_weasyprint_css_has_all_typography_tokens() -> None:
    report = audit_generated_css(get_weasyprint_css_path())
    assert report.status is AuditStatus.PASS, [(f.rule, f.expected) for f in report.findings]
