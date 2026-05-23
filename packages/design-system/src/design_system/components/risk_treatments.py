"""Three locked RiskTreatment constants (T017).

Locked by spec FR-007 + data-model section 8. `color.signal` is shared
with the CTA accent — there is no separate "intense yellow" token.
"""

from __future__ import annotations

from dataclasses import dataclass

from design_system.tokens.types import RiskLevel


@dataclass(frozen=True, slots=True)
class TokenBinding:
    role: str  # background | foreground | border
    token_name: str
    required: bool = True


@dataclass(frozen=True, slots=True)
class RiskTreatment:
    level: RiskLevel
    bindings: tuple[TokenBinding, ...]
    metric_weight: int
    pill_copy_en: str
    pill_copy_pt: str
    role_marker_html: str = "risk-pill"
    role_marker_pdf: str = "Risk-Pill"
    glyph: str = ""


LOW = RiskTreatment(
    level=RiskLevel.LOW,
    bindings=(
        TokenBinding(role="background", token_name="color.surface"),
        TokenBinding(role="foreground", token_name="color.muted"),
        TokenBinding(role="border", token_name="color.border"),
    ),
    metric_weight=500,
    pill_copy_en="Low risk",
    pill_copy_pt="Risco baixo",
    glyph="○",  # ○ — open circle
)

MEDIUM = RiskTreatment(
    level=RiskLevel.MEDIUM,
    bindings=(
        TokenBinding(role="background", token_name="color.surface"),
        TokenBinding(role="foreground", token_name="color.amber"),
        TokenBinding(role="border", token_name="color.amber"),
    ),
    metric_weight=600,
    pill_copy_en="Medium risk",
    pill_copy_pt="Risco médio",
    glyph="◐",  # ◐ — half-filled circle
)

HIGH = RiskTreatment(
    level=RiskLevel.HIGH,
    bindings=(
        TokenBinding(role="background", token_name="color.background"),
        TokenBinding(role="foreground", token_name="color.signal"),
        TokenBinding(role="border", token_name="color.signal"),
    ),
    metric_weight=700,
    pill_copy_en="High risk",
    pill_copy_pt="Risco alto",
    glyph="●",  # ● — filled circle
)


ALL: tuple[RiskTreatment, ...] = (LOW, MEDIUM, HIGH)
BY_LEVEL: dict[RiskLevel, RiskTreatment] = {t.level: t for t in ALL}


__all__ = [
    "ALL",
    "BY_LEVEL",
    "HIGH",
    "LOW",
    "MEDIUM",
    "RiskTreatment",
    "TokenBinding",
]
