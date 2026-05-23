"""Suspicion score + locked risk-level thresholds.

Thresholds locked by spec 001-fairplay-analysis FR-011 / Clarification Q1
(2026-05-23): low < 0.35, medium [0.35, 0.70), high >= 0.70. The
constants are exported so any consumer that classifies risk can import
them rather than hard-coding values.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

RISK_LOW_MAX: float = 0.35
"""Strict upper bound for LOW (score < RISK_LOW_MAX)."""

RISK_MEDIUM_MAX: float = 0.70
"""Strict upper bound for MEDIUM (score < RISK_MEDIUM_MAX)."""

RISK_HIGH_MIN: float = 0.70
"""Inclusive lower bound for HIGH (score >= RISK_HIGH_MIN)."""

PLY_MIN_FOR_SCORING: int = 10
"""Spec edge case: games shorter than this are ineligible for scoring."""


class RiskLevel(StrEnum):
    """Categorical risk classification driven by the locked thresholds."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def risk_level_for(score: float) -> RiskLevel:
    """Map a [0, 1] suspicion score to a categorical risk level.

    Raises ValueError if the score is outside [0, 1].
    """
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"suspicion score must be in [0, 1]; got {score}")
    if score < RISK_LOW_MAX:
        return RiskLevel.LOW
    if score < RISK_MEDIUM_MAX:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH


class SuspicionScore(BaseModel):
    """Per-game or aggregated suspicion score with confidence interval."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    confidence_interval: tuple[float, float] = Field(description="Bootstrap 95% CI; (low, high).")
    bootstrap_samples: int = Field(default=1000, ge=1)
    dominant_signals: tuple[str, ...] = Field(
        default=(),
        description="Top contributing signal names, longest first.",
    )

    def model_post_init(self, __context: object) -> None:
        low, high = self.confidence_interval
        if not 0.0 <= low <= high <= 1.0:
            raise ValueError(
                "confidence_interval must satisfy 0 <= low <= high <= 1; "
                f"got {self.confidence_interval}"
            )
        derived = risk_level_for(self.score)
        if derived is not self.risk_level:
            raise ValueError(
                f"risk_level ({self.risk_level.value}) inconsistent with thresholds for "
                f"score={self.score}; expected {derived.value}"
            )
