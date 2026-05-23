"""Lexical compliance — narrative + templates (T048).

Asserts the actual rendered HTML/JSON for the canonical bundle yields
zero forbidden-term matches. The narrative module is exercised
end-to-end via the existing fixtures.
"""

from __future__ import annotations

import pytest
from design_system.audits.lexical import audit_text
from design_system.audits.report import AuditStatus
from report_engine.render_html import render_report_html
from report_engine.render_json import render_report_json


@pytest.mark.audit_lexical
def test_rendered_html_passes_lexical_audit(bundle) -> None:
    report = audit_text(
        render_report_html(bundle),
        languages=("en", "pt"),
        artefact_label="rendered.html",
    )
    assert report.status is AuditStatus.PASS, [f.actual for f in report.findings]


@pytest.mark.audit_lexical
def test_rendered_json_passes_lexical_audit(bundle) -> None:
    report = audit_text(
        render_report_json(bundle),
        languages=("en", "pt"),
        artefact_label="rendered.json",
    )
    assert report.status is AuditStatus.PASS, [f.actual for f in report.findings]


@pytest.mark.audit_lexical
def test_template_source_passes_lexical_audit() -> None:
    from pathlib import Path

    template = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "report_engine"
        / "templates"
        / "single_game.html.j2"
    )
    report = audit_text(
        template.read_text(),
        languages=("en", "pt"),
        artefact_label=str(template),
    )
    assert report.status is AuditStatus.PASS, [f.actual for f in report.findings]
