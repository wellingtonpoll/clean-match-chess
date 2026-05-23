"""JSON-driven component catalogue (T076).

The canonical source is `catalogue.json` in this directory. The dict
exposed here loads it at import time; mutation is not supported.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from design_system.components.risk_treatments import ALL as ALL_RISK_TREATMENTS
from design_system.components.risk_treatments import RiskTreatment

CATALOGUE_FILE: Final[Path] = Path(__file__).resolve().parent / "catalogue.json"


@dataclass(frozen=True, slots=True)
class AccessibilityRequirement:
    min_contrast_text: float | None
    min_contrast_non_text: float | None
    keyboard_focusable: bool
    aria_role: str | None


@dataclass(frozen=True, slots=True)
class Component:
    name: str
    description: str
    tokens_of_record: tuple[str, ...]
    states: tuple[str, ...]
    surfaces: frozenset[str]
    accessibility: AccessibilityRequirement
    added_in: str


def _coerce_accessibility(payload: dict[str, Any]) -> AccessibilityRequirement:
    return AccessibilityRequirement(
        min_contrast_text=payload.get("min_contrast_text"),
        min_contrast_non_text=payload.get("min_contrast_non_text"),
        keyboard_focusable=bool(payload.get("keyboard_focusable", False)),
        aria_role=payload.get("aria_role"),
    )


def _load_components(path: Path = CATALOGUE_FILE) -> dict[str, Component]:
    payload = json.loads(path.read_text())
    out: dict[str, Component] = {}
    for name, entry in payload.get("components", {}).items():
        out[name] = Component(
            name=name,
            description=entry["description"],
            tokens_of_record=tuple(entry["tokens_of_record"]),
            states=tuple(entry["states"]),
            surfaces=frozenset(entry["surfaces"]),
            accessibility=_coerce_accessibility(entry["accessibility"]),
            added_in=entry["added_in"],
        )
    return out


COMPONENTS: dict[str, Component] = _load_components()


def get(name: str) -> Component:
    if name not in COMPONENTS:
        raise KeyError(f"component {name!r} not in catalogue")
    return COMPONENTS[name]


def names() -> tuple[str, ...]:
    return tuple(sorted(COMPONENTS))


def all_risk_treatments() -> tuple[RiskTreatment, ...]:
    return ALL_RISK_TREATMENTS


__all__ = [
    "CATALOGUE_FILE",
    "COMPONENTS",
    "AccessibilityRequirement",
    "Component",
    "all_risk_treatments",
    "get",
    "names",
]
