"""Palette compliance — design-system Track A on bundled adapter (T045)."""

from __future__ import annotations

import pytest
from design_system.audits.palette import audit_generated_css
from design_system.audits.report import AuditStatus
from report_engine.styles import get_weasyprint_css_path


@pytest.mark.audit_palette
def test_bundled_weasyprint_css_passes_palette_audit() -> None:
    report = audit_generated_css(get_weasyprint_css_path())
    assert report.status is AuditStatus.PASS, [(f.rule, f.actual) for f in report.findings]
