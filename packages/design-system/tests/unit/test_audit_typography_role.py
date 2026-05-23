"""Typography role-marker audit (T091 — A2 remediation).

Per `contracts/audit-typography.md` § "Headline metric definition":
- A node carrying `typography.metric` (class `.metric`) WITHOUT an
  ancestor or self with `data-role="metric-card-headline"` fails with
  rule `missing_metric_role`.
- A node carrying `data-role="metric-card-headline"` whose metric
  child does NOT use `typography.metric` (class `.metric`) fails
  with rule `wrong_metric_typography`.
- A tagged + correctly-typed node passes.
"""

from __future__ import annotations

from pathlib import Path

from design_system.audits.report import AuditStatus
from design_system.audits.typography import audit_html

_TEMPLATE_PASS = """<!DOCTYPE html><html lang="en"><body>
<section data-role="metric-card-headline">
  <span class="metric">0.42</span>
</section>
</body></html>"""

_TEMPLATE_UNTAGGED = """<!DOCTYPE html><html lang="en"><body>
<section>
  <span class="metric">0.42</span>
</section>
</body></html>"""

_TEMPLATE_WRONG_TYPE = """<!DOCTYPE html><html lang="en"><body>
<section data-role="metric-card-headline">
  <span class="body">0.42</span>
</section>
</body></html>"""


def _write(tmp_path: Path, html: str) -> Path:
    out = tmp_path / "report.html"
    out.write_text(html)
    return out


def test_tagged_and_correct_passes(tmp_path: Path) -> None:
    report = audit_html(_write(tmp_path, _TEMPLATE_PASS))
    assert report.status is AuditStatus.PASS, [f.rule for f in report.findings]


def test_untagged_metric_emits_missing_metric_role(tmp_path: Path) -> None:
    report = audit_html(_write(tmp_path, _TEMPLATE_UNTAGGED))
    assert report.status is AuditStatus.FAIL
    rules = {f.rule for f in report.findings}
    assert "missing_metric_role" in rules


def test_tagged_but_wrong_typography_emits_rule(tmp_path: Path) -> None:
    report = audit_html(_write(tmp_path, _TEMPLATE_WRONG_TYPE))
    assert report.status is AuditStatus.FAIL
    rules = {f.rule for f in report.findings}
    assert "wrong_metric_typography" in rules


def test_audit_html_no_metric_no_findings(tmp_path: Path) -> None:
    html = "<!DOCTYPE html><html><body><p>nothing to audit</p></body></html>"
    report = audit_html(_write(tmp_path, html))
    assert report.status is AuditStatus.PASS
