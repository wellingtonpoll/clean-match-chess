"""Motion static-CSS compliance (T047)."""

from __future__ import annotations

import pytest
from design_system.audits.motion import audit_static_css
from design_system.audits.report import AuditStatus
from report_engine.styles import get_weasyprint_css_path


@pytest.mark.audit_motion
def test_bundled_weasyprint_css_has_no_motion_drift() -> None:
    """PDF surface has no animations; motion audit passes trivially."""
    report = audit_static_css(get_weasyprint_css_path())
    assert report.status is AuditStatus.PASS, [(f.rule, f.actual) for f in report.findings]
