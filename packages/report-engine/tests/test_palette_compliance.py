"""Palette compliance — design-system Track A + Track C (T045 + T095)."""

from __future__ import annotations

from pathlib import Path

import pytest
from design_system.audits.palette import audit_generated_css, audit_risk_indicators
from design_system.audits.report import AuditStatus
from report_engine.render_html import render_report_html
from report_engine.styles import get_weasyprint_css_path


@pytest.mark.audit_palette
def test_bundled_weasyprint_css_passes_palette_audit() -> None:
    report = audit_generated_css(get_weasyprint_css_path())
    assert report.status is AuditStatus.PASS, [(f.rule, f.actual) for f in report.findings]


@pytest.mark.audit_palette
def test_rendered_html_passes_track_c_risk_audit(bundle, tmp_path: Path) -> None:
    html = render_report_html(bundle)
    artefact = tmp_path / "report.html"
    artefact.write_text(html)
    report = audit_risk_indicators(artefact)
    assert report.status is AuditStatus.PASS, [(f.rule, f.actual) for f in report.findings]
