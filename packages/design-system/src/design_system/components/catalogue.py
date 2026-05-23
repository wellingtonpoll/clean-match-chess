"""Component catalogue loader (T016).

MVP catalogue is a small immutable dict mapping component name to
its tokens-of-record + supported surfaces + state list. The full
JSON-driven catalogue is a Phase-5 task (T076) for feature 002 US3.
"""

from __future__ import annotations

from dataclasses import dataclass

from design_system.components.risk_treatments import ALL as ALL_RISK_TREATMENTS
from design_system.components.risk_treatments import RiskTreatment


@dataclass(frozen=True, slots=True)
class Component:
    name: str
    description: str
    tokens_of_record: tuple[str, ...]
    states: tuple[str, ...]
    surfaces: frozenset[str]


COMPONENTS: dict[str, Component] = {
    "analytical-card": Component(
        name="analytical-card",
        description="Large dark surface card carrying a headline metric and supporting copy.",
        tokens_of_record=(
            "color.surface",
            "color.border",
            "color.text",
            "color.muted",
            "color.signal",
            "radius.lg",
            "spacing.4",
            "spacing.6",
            "typography.metric",
            "typography.body",
            "shadow.card",
        ),
        states=("default",),
        surfaces=frozenset({"pdf", "html", "web"}),
    ),
    "risk-pill": Component(
        name="risk-pill",
        description="Categorical risk indicator (LOW / MEDIUM / HIGH) with role marker.",
        tokens_of_record=(
            "color.background",
            "color.surface",
            "color.muted",
            "color.amber",
            "color.signal",
            "color.border",
            "radius.sm",
            "typography.body_medium",
        ),
        states=("default",),
        surfaces=frozenset({"pdf", "html", "web"}),
    ),
    "timeline": Component(
        name="timeline",
        description="Per-ply ribbon with regime markers and complexity heatmap.",
        tokens_of_record=(
            "color.background",
            "color.surface",
            "color.signal",
            "color.amber",
            "color.muted",
            "spacing.2",
            "spacing.4",
        ),
        states=("default", "hover"),
        surfaces=frozenset({"html", "web"}),
    ),
    "heuristic-badge": Component(
        name="heuristic-badge",
        description="Signal name + version pill (e.g., engine-correlation@0.1.0).",
        tokens_of_record=(
            "color.surface",
            "color.muted",
            "color.text",
            "radius.sm",
            "typography.body",
        ),
        states=("default",),
        surfaces=frozenset({"pdf", "html", "web"}),
    ),
    "manifest-block": Component(
        name="manifest-block",
        description="Tabular block listing reproducibility manifest fields.",
        tokens_of_record=(
            "color.surface",
            "color.border",
            "color.text",
            "color.muted",
            "spacing.3",
            "typography.body",
        ),
        states=("default",),
        surfaces=frozenset({"pdf", "html", "web"}),
    ),
    "code-inline": Component(
        name="code-inline",
        description="Inline monospace span for hashes, hex values, identifiers.",
        tokens_of_record=("color.surface", "color.text", "typography.body"),
        states=("default",),
        surfaces=frozenset({"pdf", "html", "web"}),
    ),
}


def get(name: str) -> Component:
    if name not in COMPONENTS:
        raise KeyError(f"component {name!r} not in catalogue")
    return COMPONENTS[name]


def names() -> tuple[str, ...]:
    return tuple(sorted(COMPONENTS))


def all_risk_treatments() -> tuple[RiskTreatment, ...]:
    return ALL_RISK_TREATMENTS


__all__ = ["COMPONENTS", "Component", "all_risk_treatments", "get", "names"]
