"""Locked risk thresholds, versioned for manifest provenance.

The numeric cutoffs live in `shared_types.score` so any package can
classify a score uniformly. This module wraps them with a semver
version string that gets stamped into the reproducibility manifest;
changing the thresholds (a MAJOR-bump-class event) requires editing
SCORING_THRESHOLDS_VERSION alongside shared_types.score.
"""

from __future__ import annotations

from typing import Final

from shared_types.score import (
    RISK_HIGH_MIN,
    RISK_LOW_MAX,
    RISK_MEDIUM_MAX,
    RiskLevel,
    risk_level_for,
)

SCORING_THRESHOLDS_VERSION: Final[str] = "1.0.0"


def thresholds_snapshot() -> dict[str, float | str]:
    """Snapshot of every value the manifest needs to record."""
    return {
        "version": SCORING_THRESHOLDS_VERSION,
        "risk_low_max": RISK_LOW_MAX,
        "risk_medium_max": RISK_MEDIUM_MAX,
        "risk_high_min": RISK_HIGH_MIN,
    }


def risk_level(score: float) -> RiskLevel:
    """Pure passthrough to keep the heuristics-layer import surface narrow."""
    return risk_level_for(score)
