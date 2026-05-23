"""Palette audit: Track A CSS lint + Track B pixel + Track C risk role.

Track A is the only one wired in MVP. Tracks B and C land alongside
the Phase-3 frontend (rasterisation + DOM-walk dependencies are
heavier).
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
    TrackResult,
)
from design_system.tokens.compile_weasyprint import DEFAULT_TOKEN_FILE
from design_system.tokens.loader import (
    FORBIDDEN_HUE_RANGES,
    FORBIDDEN_SATURATION_THRESHOLD,
    TokenFile,
    load_token_file,
)
from design_system.tokens.types import ColourValue

_HEX_RE = re.compile(r"#([0-9a-fA-F]{6})\b")


def audit_generated_css(
    css_path: Path,
    tokens: TokenFile | None = None,
) -> AuditReport:
    """Track A: every literal #xxxxxx in the CSS MUST be a known token."""
    tokens = tokens or load_token_file(DEFAULT_TOKEN_FILE)
    started = datetime.now(UTC)
    findings: list[AuditFinding] = []

    palette_hex = {c.hex.upper() for c in tokens.colours.values()}
    text = css_path.read_text()

    for match in _HEX_RE.finditer(text):
        observed = "#" + match.group(1).upper()
        if observed not in palette_hex:
            findings.append(
                AuditFinding(
                    severity=Severity.BLOCK,
                    rule="unknown_color_literal",
                    location=f"{css_path}:{_line_of(text, match.start())}",
                    expected=", ".join(sorted(palette_hex)),
                    actual=observed,
                    message=f"colour literal {observed} not in locked palette",
                )
            )
        else:
            colour = ColourValue(hex=observed)
            hue, sat, _ = colour.hsl
            if sat > FORBIDDEN_SATURATION_THRESHOLD and any(
                lo <= hue <= hi for lo, hi in FORBIDDEN_HUE_RANGES
            ):
                findings.append(
                    AuditFinding(
                        severity=Severity.BLOCK,
                        rule="forbidden_hue",
                        location=f"{css_path}:{_line_of(text, match.start())}",
                        expected="hue outside [350-360]+[0-20] at saturation > 30%",
                        actual=f"hue={hue:.1f} sat={sat:.1f}",
                        message=f"colour {observed} is in the forbidden hue range",
                    )
                )

    finished = datetime.now(UTC)
    status = AuditStatus.PASS if not findings else AuditStatus.FAIL
    return AuditReport(
        audit_name=AuditName.PALETTE,
        artefact=str(css_path),
        started_at=started,
        finished_at=finished,
        status=status,
        findings=tuple(findings),
        tracks={"css": TrackResult(name="css", status=status, findings=tuple(findings))},
    )


def audit_pdf(
    pdf_path: Path,
    tokens: TokenFile | None = None,  # noqa: ARG001 - reserved for Track B
    *,
    delta_e_threshold: float = 5.0,  # noqa: ARG001 - reserved for Track B
    fringe_tolerance: float = 0.01,  # noqa: ARG001 - reserved for Track B
) -> AuditReport:
    """Track B: pixel audit. Deferred (raster + Delta-E heavy)."""
    now = datetime.now(UTC)
    return _skipped_report(
        AuditName.PALETTE,
        str(pdf_path),
        now,
        "track-b-pixel",
        "Track B (pixel audit) deferred to Phase 3 web surfaces feature.",
    )


def audit_risk_indicators(
    artefact_path: Path,
    tokens: TokenFile | None = None,  # noqa: ARG001 - reserved for Track C
) -> AuditReport:
    """Track C: risk-indicator role check. Deferred (HTML/PDF DOM walk)."""
    now = datetime.now(UTC)
    return _skipped_report(
        AuditName.PALETTE,
        str(artefact_path),
        now,
        "track-c-risk",
        "Track C (risk-indicator role check) deferred until DOM-walk tooling lands.",
    )


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _skipped_report(
    audit: AuditName, artefact: str, now: datetime, track_name: str, message: str
) -> AuditReport:
    finding = AuditFinding(
        severity=Severity.WARN,
        rule=f"{track_name}_deferred",
        location=artefact,
        expected="audit executed",
        actual="skipped",
        message=message,
    )
    return AuditReport(
        audit_name=audit,
        artefact=artefact,
        started_at=now,
        finished_at=now,
        status=AuditStatus.PASS,  # WARN-only, non-blocking
        findings=(finding,),
    )
