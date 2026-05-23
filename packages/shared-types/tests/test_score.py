"""Threshold-to-risk-level mapping and SuspicionScore invariants."""

from __future__ import annotations

import pytest
from shared_types.score import (
    RISK_HIGH_MIN,
    RISK_LOW_MAX,
    RISK_MEDIUM_MAX,
    RiskLevel,
    SuspicionScore,
    risk_level_for,
)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, RiskLevel.LOW),
        (0.34, RiskLevel.LOW),
        (0.3499, RiskLevel.LOW),
        (RISK_LOW_MAX, RiskLevel.MEDIUM),
        (0.5, RiskLevel.MEDIUM),
        (0.6999, RiskLevel.MEDIUM),
        (RISK_MEDIUM_MAX, RiskLevel.HIGH),
        (RISK_HIGH_MIN, RiskLevel.HIGH),
        (0.99, RiskLevel.HIGH),
        (1.0, RiskLevel.HIGH),
    ],
)
def test_risk_level_for(score: float, expected: RiskLevel) -> None:
    assert risk_level_for(score) is expected


@pytest.mark.parametrize("bad", [-0.01, 1.01, 2.0, -1.0])
def test_risk_level_for_out_of_range(bad: float) -> None:
    with pytest.raises(ValueError):
        risk_level_for(bad)


def test_suspicion_score_consistency_holds() -> None:
    s = SuspicionScore(
        score=0.74,
        risk_level=RiskLevel.HIGH,
        confidence_interval=(0.66, 0.81),
    )
    assert s.bootstrap_samples == 1000


def test_suspicion_score_inconsistent_level_rejected() -> None:
    with pytest.raises(ValueError):
        SuspicionScore(
            score=0.20,
            risk_level=RiskLevel.HIGH,
            confidence_interval=(0.0, 0.5),
        )


def test_suspicion_score_invalid_ci_rejected() -> None:
    with pytest.raises(ValueError):
        SuspicionScore(
            score=0.5,
            risk_level=RiskLevel.MEDIUM,
            confidence_interval=(0.8, 0.2),
        )
