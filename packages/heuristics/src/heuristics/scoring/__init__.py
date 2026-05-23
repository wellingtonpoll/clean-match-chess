"""Score aggregation + locked risk thresholds (re-exports)."""

from heuristics.scoring.aggregator import (
    BOOTSTRAP_SAMPLES_DEFAULT,
    WEIGHTS,
    aggregate_score,
)
from heuristics.scoring.thresholds import (
    SCORING_THRESHOLDS_VERSION,
    risk_level,
    thresholds_snapshot,
)

__all__ = [
    "BOOTSTRAP_SAMPLES_DEFAULT",
    "SCORING_THRESHOLDS_VERSION",
    "WEIGHTS",
    "aggregate_score",
    "risk_level",
    "thresholds_snapshot",
]
