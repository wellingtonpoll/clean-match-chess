"""Timing-analysis signal (FR-010 timing subset).

Returns the fraction of moves where time_spent_ms is implausibly fast
for the position's complexity. Without timing data, returns 0 with a
zero sample count (signal silenced).
"""

from __future__ import annotations

from shared_types.game import Move, Position
from shared_types.signal import HeuristicVersion, SignalAggregate

__signal_name__ = "timing-analysis"
__signal_version__ = "0.1.0"

_FAST_THRESHOLD_MS = 1500
_COMPLEX_THRESHOLD = 0.5


def signal_version() -> HeuristicVersion:
    return HeuristicVersion(
        name=__signal_name__,
        version=__signal_version__,
        git_sha="0000000",
        owner="cleanmatch",
        changelog_path="packages/heuristics/CHANGELOG.md",
    )


def timing_anomaly(
    positions: tuple[Position, ...],
    moves: tuple[Move, ...],
) -> SignalAggregate:
    eligible = [
        (positions[i], moves[i])
        for i in range(min(len(positions), len(moves)))
        if moves[i].time_spent_ms is not None and positions[i].complexity is not None
    ]
    if not eligible:
        return SignalAggregate(
            signal_name=__signal_name__,
            signal_version=__signal_version__,
            mean=0.0,
            weighted_mean=0.0,
            samples=0,
        )
    anomalies = sum(
        1
        for pos, mv in eligible
        if mv.time_spent_ms is not None
        and pos.complexity is not None
        and mv.time_spent_ms < _FAST_THRESHOLD_MS
        and pos.complexity.composite > _COMPLEX_THRESHOLD
    )
    value = anomalies / len(eligible)
    return SignalAggregate(
        signal_name=__signal_name__,
        signal_version=__signal_version__,
        mean=value,
        weighted_mean=value,
        samples=len(eligible),
    )
