"""Complexity-analysis signal (FR-006).

Aggregates per-position `ComplexityScore.composite` over the analysed
positions. Higher mean = busier game; the value itself is not
suspicious — the *correlation* between high complexity and high engine
agreement is what feeds the suspicion score (handled by
`engine_correlation`).
"""

from __future__ import annotations

from statistics import mean

from shared_types.game import Position
from shared_types.signal import HeuristicVersion, SignalAggregate

__signal_name__ = "complexity-analysis"
__signal_version__ = "0.1.0"


def signal_version() -> HeuristicVersion:
    return HeuristicVersion(
        name=__signal_name__,
        version=__signal_version__,
        git_sha="0000000",
        owner="cleanmatch",
        changelog_path="packages/heuristics/CHANGELOG.md",
    )


def complexity_score(positions: tuple[Position, ...]) -> SignalAggregate:
    if not positions:
        return _empty()
    values = [p.complexity.composite for p in positions if p.complexity is not None]
    if not values:
        return _empty()
    avg = mean(values)
    return SignalAggregate(
        signal_name=__signal_name__,
        signal_version=__signal_version__,
        mean=avg,
        weighted_mean=avg,
        samples=len(values),
    )


def _empty() -> SignalAggregate:
    return SignalAggregate(
        signal_name=__signal_name__,
        signal_version=__signal_version__,
        mean=0.0,
        weighted_mean=0.0,
        samples=0,
    )
