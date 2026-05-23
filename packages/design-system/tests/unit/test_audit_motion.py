"""Motion-audit static-CSS scan (T038)."""

from __future__ import annotations

from pathlib import Path

from design_system.audits.motion import audit_static_css
from design_system.audits.report import AuditStatus
from design_system.tokens.compile_weasyprint import DEFAULT_OUTPUT


def test_committed_css_has_no_transitions() -> None:
    """PDF surface has no animations; static audit passes trivially."""
    report = audit_static_css(Path(DEFAULT_OUTPUT))
    assert report.status is AuditStatus.PASS
    assert report.findings == ()


def test_literal_easing_rejected(tmp_path: Path) -> None:
    css = tmp_path / "bad.css"
    css.write_text(".x { transition: opacity 250ms linear; }\n")
    report = audit_static_css(css)
    assert report.status is AuditStatus.FAIL
    rules = {f.rule for f in report.findings}
    assert "motion_wrong_easing" in rules


def test_out_of_range_duration_rejected(tmp_path: Path) -> None:
    css = tmp_path / "bad.css"
    css.write_text(".x { transition: opacity 500ms var(--motion-easing-standard); }\n")
    report = audit_static_css(css)
    assert report.status is AuditStatus.FAIL
    rules = {f.rule for f in report.findings}
    assert "motion_out_of_range" in rules


def test_token_only_transition_passes(tmp_path: Path) -> None:
    css = tmp_path / "ok.css"
    css.write_text(".x { transition: opacity 250ms var(--motion-easing-standard); }\n")
    report = audit_static_css(css)
    assert report.status is AuditStatus.PASS
