"""Regime-shift signal (FR-007 / FR-010).

Detects an abrupt change in per-move "accuracy" (cp loss vs engine top)
across consecutive segments. Returns one `SignalAggregate` summarising
the maximum absolute mean-shift between adjacent segments.
"""

from __future__ import annotations

from itertools import pairwise
from statistics import mean

from shared_types.signal import HeuristicVersion, Segment, SignalAggregate

__signal_name__ = "regime-shift"
__signal_version__ = "0.1.0"


def signal_version() -> HeuristicVersion:
    return HeuristicVersion(
        name=__signal_name__,
        version=__signal_version__,
        git_sha="0000000",
        owner="cleanmatch",
        changelog_path="packages/heuristics/CHANGELOG.md",
    )


def regime_shift_score(segments: tuple[Segment, ...]) -> SignalAggregate:
    """Return one aggregate; higher = bigger shift across phases."""
    if len(segments) < 2:
        return SignalAggregate(
            signal_name=__signal_name__,
            signal_version=__signal_version__,
            mean=0.0,
            weighted_mean=0.0,
            samples=len(segments),
        )

    sizes = [_segment_size(s) for s in segments]
    deltas = [abs(b - a) for a, b in pairwise(sizes)]
    avg_size = max(1.0, mean(sizes))
    normalised = max(deltas) / avg_size if deltas else 0.0
    bounded = max(0.0, min(1.0, normalised))
    return SignalAggregate(
        signal_name=__signal_name__,
        signal_version=__signal_version__,
        mean=bounded,
        weighted_mean=bounded,
        samples=len(segments),
    )


def _segment_size(segment: Segment) -> float:
    start, end = segment.ply_range
    return max(0.0, float(end - start))
