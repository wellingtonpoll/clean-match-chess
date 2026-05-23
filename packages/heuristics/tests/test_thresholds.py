"""Thresholds module pinning + snapshot shape."""

from __future__ import annotations

from heuristics.scoring.thresholds import (
    SCORING_THRESHOLDS_VERSION,
    risk_level,
    thresholds_snapshot,
)
from shared_types.score import RiskLevel


def test_version_pinned_v1() -> None:
    assert SCORING_THRESHOLDS_VERSION == "1.0.0"


def test_snapshot_carries_locked_values() -> None:
    snap = thresholds_snapshot()
    assert snap == {
        "version": "1.0.0",
        "risk_low_max": 0.35,
        "risk_medium_max": 0.70,
        "risk_high_min": 0.70,
    }


def test_passthrough_classifier() -> None:
    assert risk_level(0.10) is RiskLevel.LOW
    assert risk_level(0.50) is RiskLevel.MEDIUM
    assert risk_level(0.90) is RiskLevel.HIGH
