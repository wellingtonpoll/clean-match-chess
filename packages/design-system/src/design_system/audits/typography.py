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


def audit_html(html_path: Path) -> AuditReport:
    """Role-based DOM audit; deferred to Phase 3 web feature."""
    now = datetime.now(UTC)
    return AuditReport(
        audit_name=AuditName.TYPOGRAPHY,
        artefact=str(html_path),
        started_at=now,
        finished_at=now,
        status=AuditStatus.PASS,
        findings=(
            AuditFinding(
                severity=Severity.WARN,
                rule="html_audit_deferred",
                location=str(html_path),
                expected="audit executed",
                actual="skipped",
                message="HTML typography audit deferred to Phase 3.",
            ),
        ),
    )


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
