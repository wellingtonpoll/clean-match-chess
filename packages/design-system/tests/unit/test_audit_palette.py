"""Palette audit Track A (T031)."""

from __future__ import annotations

from pathlib import Path

from design_system.audits.palette import audit_generated_css
from design_system.audits.report import AuditName, AuditStatus
from design_system.tokens.compile_weasyprint import DEFAULT_OUTPUT


def test_committed_css_passes_palette_audit() -> None:
    report = audit_generated_css(Path(DEFAULT_OUTPUT))
    assert report.audit_name is AuditName.PALETTE
    assert report.status is AuditStatus.PASS
    assert report.findings == ()


def test_unknown_literal_color_rejected(tmp_path: Path) -> None:
    css = tmp_path / "bad.css"
    css.write_text(":root { --evil: #112233; }\n")
    report = audit_generated_css(css)
    assert report.status is AuditStatus.FAIL
    assert any(f.rule == "unknown_color_literal" for f in report.findings)


def test_forbidden_hue_literal_rejected(tmp_path: Path) -> None:
    # #FF0000 isn't in palette anyway; assert it trips unknown_color_literal
    # plus the forbidden-hue track ideally.
    css = tmp_path / "red.css"
    css.write_text(":root { --danger: #FF0000; }\n")
    report = audit_generated_css(css)
    assert report.status is AuditStatus.FAIL
    rules = {f.rule for f in report.findings}
    assert "unknown_color_literal" in rules
