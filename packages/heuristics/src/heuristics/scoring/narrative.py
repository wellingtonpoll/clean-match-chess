"""Plain-language rationale strings per signal (T059, FR-012).

Each entry maps a `signal_name` to a templated rationale describing
what the signal value means for the contributing move. The strings
deliberately use analytical vocabulary (per design-system spec
FR-011) and never assert wrongdoing.

The templates accept a single positional `{value:.2f}` placeholder.
Consumers (report-engine in feature 002) format with the per-move or
per-segment signal value.
"""

from __future__ import annotations

from typing import Final

RATIONALE_TEMPLATES: Final[dict[str, str]] = {
    "engine-correlation/top1": (
        "Player's move matched the engine's preferred move (top-1 agreement rate: {value:.2f})."
    ),
    "engine-correlation/top3": (
        "Player's move appeared in the engine's top three (top-3 agreement rate: {value:.2f})."
    ),
    "engine-correlation/weighted": (
        "Complexity-weighted agreement with the engine's top line "
        "(weighted match rate: {value:.2f})."
    ),
    "complexity-analysis": (
        "Average positional complexity over the analysed game (composite score: {value:.2f})."
    ),
    "tactical-detection": (
        "Fraction of positions flagged as tactically critical (critical density: {value:.2f})."
    ),
    "regime-shift": (
        "Largest behavioural shift detected between consecutive game "
        "segments (normalised magnitude: {value:.2f})."
    ),
    "behavioral-patterns/precision-burst": (
        "Longest streak of consecutive top-engine moves, normalised "
        "by game length (burst score: {value:.2f})."
    ),
    "behavioral-patterns/blunder-suppression": (
        "Fraction of complex positions where no significant blunder "
        "occurred (suppression rate: {value:.2f})."
    ),
    "timing-analysis": (
        "Fraction of moves played implausibly fast for the position's "
        "complexity (timing anomaly rate: {value:.2f})."
    ),
    "segment-size": ("Number of plies in this segment (raw count: {value:.2f})."),
}


def rationale_for(signal_name: str, value: float) -> str:
    """Plain-language rationale for one signal's contribution."""
    template = RATIONALE_TEMPLATES.get(signal_name)
    if template is None:
        return f"Signal {signal_name} contributed value {value:.2f}."
    return template.format(value=value)
