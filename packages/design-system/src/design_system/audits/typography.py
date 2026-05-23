"""Typography audit (T035-T037).

Static scan of generated CSS for the required typography tokens.
HTML/PDF role-based audit (selectolax/pdfminer) deferred — wired
alongside actual rendered artefacts.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from design_system.audits.report import (
    AuditFinding,
    AuditName,
    AuditReport,
    AuditStatus,
    Severity,
)
from design_system.tokens.compile_weasyprint import DEFAULT_TOKEN_FILE
from design_system.tokens.loader import TokenFile, load_token_file

REQUIRED_TYPOGRAPHY_TOKENS = ("h1", "h2", "body", "body_medium", "metric")


def audit_generated_css(
    css_path: Path,
    tokens: TokenFile | None = None,
) -> AuditReport:
    """Assert every required typography token appears in the compiled CSS."""
    tokens = tokens or load_token_file(DEFAULT_TOKEN_FILE)
    started = datetime.now(UTC)
    findings: list[AuditFinding] = []
    text = css_path.read_text()

    for token in REQUIRED_TYPOGRAPHY_TOKENS:
        pattern = re.compile(
            r"--typography-typography-" + re.escape(token) + r"-\w+:",
        )
        if not pattern.search(text):
            findings.append(
                AuditFinding(
                    severity=Severity.BLOCK,
                    rule="missing_typography_token",
                    location=str(css_path),
                    expected=f"typography.{token}",
                    actual="absent",
                    message=f"typography token {token!r} missing from compiled CSS",
                )
            )

    finished = datetime.now(UTC)
    status = AuditStatus.PASS if not findings else AuditStatus.FAIL
    return AuditReport(
        audit_name=AuditName.TYPOGRAPHY,
        artefact=str(css_path),
        started_at=started,
        finished_at=finished,
        status=status,
        findings=tuple(findings),
    )


_METRIC_CLASS = "metric"
_METRIC_ROLE = "metric-card-headline"


def audit_html(html_path: Path) -> AuditReport:
    """Role-marker DOM audit (T092 — A2 remediation).

    Asserts producer-side typography role contract:
    - Every `.metric` node MUST live inside a node with
      `data-role="metric-card-headline"` (else rule
      `missing_metric_role`).
    - Every node with `data-role="metric-card-headline"` MUST contain
      at least one `.metric` descendant (else rule
      `wrong_metric_typography`).
    """
    from selectolax.parser import HTMLParser

    started = datetime.now(UTC)
    findings: list[AuditFinding] = []
    text = html_path.read_text()
    tree = HTMLParser(text)

    for metric_node in tree.css(f".{_METRIC_CLASS}"):
        if _ancestor_with_role(metric_node, _METRIC_ROLE) is None:
            findings.append(
                AuditFinding(
                    severity=Severity.BLOCK,
                    rule="missing_metric_role",
                    location=str(html_path),
                    expected=f'data-role="{_METRIC_ROLE}" on ancestor',
                    actual="no role marker",
                    message=(
                        f"node with class {_METRIC_CLASS!r} has no "
                        f"{_METRIC_ROLE!r} ancestor; producer must tag the container"
                    ),
                )
            )

    for headline_node in tree.css(f'[data-role="{_METRIC_ROLE}"]'):
        if not headline_node.css(f".{_METRIC_CLASS}"):
            findings.append(
                AuditFinding(
                    severity=Severity.BLOCK,
                    rule="wrong_metric_typography",
                    location=str(html_path),
                    expected=f"descendant with class {_METRIC_CLASS!r} using typography.metric",
                    actual="no .metric descendant",
                    message=(
                        f"node with data-role={_METRIC_ROLE!r} carries headline "
                        "semantics but its numeral does not use typography.metric"
                    ),
                )
            )

    finished = datetime.now(UTC)
    status = AuditStatus.PASS if not findings else AuditStatus.FAIL
    return AuditReport(
        audit_name=AuditName.TYPOGRAPHY,
        artefact=str(html_path),
        started_at=started,
        finished_at=finished,
        status=status,
        findings=tuple(findings),
    )


def _ancestor_with_role(node: object, role: str) -> object | None:
    """Walk up the DOM looking for `data-role="<role>"` on self or ancestors."""
    current: object | None = node
    while current is not None:
        attrs = getattr(current, "attributes", {}) or {}
        if attrs.get("data-role") == role:
            return current
        current = getattr(current, "parent", None)
    return None


def audit_pdf(pdf_path: Path) -> AuditReport:
    """PDF structure-tree audit; deferred."""
    now = datetime.now(UTC)
    return AuditReport(
        audit_name=AuditName.TYPOGRAPHY,
        artefact=str(pdf_path),
        started_at=now,
        finished_at=now,
        status=AuditStatus.PASS,
        findings=(
            AuditFinding(
                severity=Severity.WARN,
                rule="pdf_audit_deferred",
                location=str(pdf_path),
                expected="audit executed",
                actual="skipped",
                message="PDF typography audit deferred to Phase 3.",
            ),
        ),
    )
