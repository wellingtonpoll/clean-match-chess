"""Track-C risk-indicator role audit (T093 — C2/I1 remediation).

Per `contracts/audit-palette.md` § "Track C":
- A node tagged `data-role="risk-pill"` whose colour class is NOT
  one of the three canonical recipes
  (`risk-low`/`risk-medium`/`risk-high`) fails with rule
  `risk_treatment_non_canonical`.
- A node carrying a risk colour class but lacking
  `data-role="risk-pill"` fails with rule `missing_risk_role`.
- Tagged + canonical (for each of LOW / MEDIUM / HIGH) passes.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from design_system.audits.palette import audit_risk_indicators
from design_system.audits.report import AuditStatus


def _wrap(snippet: str) -> str:
    return f"<!DOCTYPE html><html lang='en'><body>{snippet}</body></html>"


def _write(tmp_path: Path, html: str) -> Path:
    out = tmp_path / "report.html"
    out.write_text(html)
    return out


@pytest.mark.parametrize("level", ["low", "medium", "high"])
def test_canonical_risk_passes(tmp_path: Path, level: str) -> None:
    html = _wrap(f'<span data-role="risk-pill" class="risk-{level}">{level}</span>')
    report = audit_risk_indicators(_write(tmp_path, html))
    assert report.status is AuditStatus.PASS, [f.rule for f in report.findings]


def test_tagged_but_non_canonical_class_fails(tmp_path: Path) -> None:
    html = _wrap('<span data-role="risk-pill" class="risk-extreme">!</span>')
    report = audit_risk_indicators(_write(tmp_path, html))
    assert report.status is AuditStatus.FAIL
    rules = {f.rule for f in report.findings}
    assert "risk_treatment_non_canonical" in rules


def test_tagged_without_class_fails(tmp_path: Path) -> None:
    html = _wrap('<span data-role="risk-pill">high</span>')
    report = audit_risk_indicators(_write(tmp_path, html))
    assert report.status is AuditStatus.FAIL
    rules = {f.rule for f in report.findings}
    assert "risk_treatment_non_canonical" in rules


def test_coloured_node_without_role_fails(tmp_path: Path) -> None:
    html = _wrap('<span class="risk-high">high</span>')
    report = audit_risk_indicators(_write(tmp_path, html))
    assert report.status is AuditStatus.FAIL
    rules = {f.rule for f in report.findings}
    assert "missing_risk_role" in rules


def test_artefact_with_no_indicators_passes(tmp_path: Path) -> None:
    html = _wrap("<p>plain text</p>")
    report = audit_risk_indicators(_write(tmp_path, html))
    assert report.status is AuditStatus.PASS
