"""Motion audit (T038-T039).

Static-CSS-only in MVP. Asserts every CSS `transition`/`animation`
declaration uses token-derived values; literal `linear`, `ease-in`,
etc. fail. Duration values outside the locked [200, 350] ms range
also fail.

Dynamic Playwright audit (Phase 3) lands when web surfaces exist.
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
from design_system.tokens.loader import LOCKED_MOTION_RANGE_MS

_TRANSITION_RE = re.compile(r"transition\s*:\s*([^;]+);", re.IGNORECASE)
_ANIMATION_RE = re.compile(r"animation\s*:\s*([^;]+);", re.IGNORECASE)
_LITERAL_DURATION_RE = re.compile(r"(\d+(?:\.\d+)?)ms\b")
_FORBIDDEN_EASING = ("linear", "ease", "ease-in", "ease-out", "ease-in-out")


def audit_static_css(css_path: Path) -> AuditReport:
    """Lint the compiled WeasyPrint CSS for non-token motion values."""
    started = datetime.now(UTC)
    findings: list[AuditFinding] = []
    text = css_path.read_text()

    for declaration in _TRANSITION_RE.findall(text) + _ANIMATION_RE.findall(text):
        for word in declaration.split():
            stripped = word.strip().strip(",;").lower()
            if stripped in _FORBIDDEN_EASING:
                findings.append(
                    AuditFinding(
                        severity=Severity.BLOCK,
                        rule="motion_wrong_easing",
                        location=str(css_path),
                        expected="var(--motion-easing-standard)",
                        actual=stripped,
                        message=f"literal easing {stripped!r} not allowed",
                    )
                )
        for match in _LITERAL_DURATION_RE.findall(declaration):
            ms = float(match)
            lo, hi = LOCKED_MOTION_RANGE_MS
            if not (lo <= ms <= hi):
                findings.append(
                    AuditFinding(
                        severity=Severity.BLOCK,
                        rule="motion_out_of_range",
                        location=str(css_path),
                        expected=f"{lo}..{hi}ms",
                        actual=f"{ms:g}ms",
                        message=f"duration {ms:g}ms outside locked range",
                    )
                )

    finished = datetime.now(UTC)
    status = AuditStatus.PASS if not findings else AuditStatus.FAIL
    return AuditReport(
        audit_name=AuditName.MOTION,
        artefact=str(css_path),
        started_at=started,
        finished_at=finished,
        status=status,
        findings=tuple(findings),
    )


def audit_web(*paths: str) -> AuditReport:
    """Dynamic web audit; deferred to Phase 3."""
    now = datetime.now(UTC)
    return AuditReport(
        audit_name=AuditName.MOTION,
        artefact=",".join(paths),
        started_at=now,
        finished_at=now,
        status=AuditStatus.PASS,
        findings=(
            AuditFinding(
                severity=Severity.WARN,
                rule="web_audit_deferred",
                location=",".join(paths),
                expected="Playwright run",
                actual="skipped",
                message="Dynamic motion audit lands with Phase 3 web surfaces.",
            ),
        ),
    )
