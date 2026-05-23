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


_CANONICAL_RISK_CLASSES: frozenset[str] = frozenset({"risk-low", "risk-medium", "risk-high"})
_RISK_ROLE_VALUE = "risk-pill"


def audit_risk_indicators(
    artefact_path: Path,
    tokens: TokenFile | None = None,  # noqa: ARG001 - reserved for full DOM walk
) -> AuditReport:
    """Track C: producer-side risk-indicator role + canonical-class check.

    HTML-only in MVP (PDF surface tagged via the source HTML template;
    PDF structure-tree walk deferred to feature 003).
    """
    from selectolax.parser import HTMLParser

    started = datetime.now(UTC)
    findings: list[AuditFinding] = []
    text = artefact_path.read_text()
    tree = HTMLParser(text)

    for node in tree.css(f'[data-role="{_RISK_ROLE_VALUE}"]'):
        classes = _classes_of(node)
        canonical = classes & _CANONICAL_RISK_CLASSES
        if not canonical:
            findings.append(
                AuditFinding(
                    severity=Severity.BLOCK,
                    rule="risk_treatment_non_canonical",
                    location=str(artefact_path),
                    expected="one of {risk-low, risk-medium, risk-high}",
                    actual=", ".join(sorted(classes)) or "no class",
                    message=(
                        "risk-pill node carries no canonical risk class "
                        "(risk-low / risk-medium / risk-high)"
                    ),
                )
            )

    for cls in _CANONICAL_RISK_CLASSES:
        for node in tree.css(f".{cls}"):
            attrs = getattr(node, "attributes", {}) or {}
            if attrs.get("data-role") != _RISK_ROLE_VALUE:
                findings.append(
                    AuditFinding(
                        severity=Severity.BLOCK,
                        rule="missing_risk_role",
                        location=str(artefact_path),
                        expected=f'data-role="{_RISK_ROLE_VALUE}"',
                        actual="absent",
                        message=(
                            f"node with class {cls!r} encodes risk colour but lacks "
                            f"the role marker data-role={_RISK_ROLE_VALUE!r}"
                        ),
                    )
                )

    finished = datetime.now(UTC)
    status = AuditStatus.PASS if not findings else AuditStatus.FAIL
    return AuditReport(
        audit_name=AuditName.PALETTE,
        artefact=str(artefact_path),
        started_at=started,
        finished_at=finished,
        status=status,
        findings=tuple(findings),
        tracks={"risk": TrackResult(name="risk", status=status, findings=tuple(findings))},
    )


def _classes_of(node: object) -> frozenset[str]:
    attrs = getattr(node, "attributes", {}) or {}
    raw = attrs.get("class", "") or ""
    return frozenset(part for part in raw.split() if part)


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
