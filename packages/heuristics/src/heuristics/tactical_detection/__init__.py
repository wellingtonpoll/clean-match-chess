"""Tactical-detection signal (FR-005).

Returns the fraction of positions flagged as `is_critical` (only-move
chains, large eval swings, high complexity, in-check positions).
Suppression: critical positions are also flagged `is_only_move` are
discounted per constitution Principle 5 — forced moves carry low
weight.
"""

from __future__ import annotations

from shared_types.game import Position
from shared_types.signal import HeuristicVersion, SignalAggregate

__signal_name__ = "tactical-detection"
__signal_version__ = "0.1.0"


def signal_version() -> HeuristicVersion:
    return HeuristicVersion(
        name=__signal_name__,
        version=__signal_version__,
        git_sha="0000000",
        owner="cleanmatch",
        changelog_path="packages/heuristics/CHANGELOG.md",
    )


def tactical_density(positions: tuple[Position, ...]) -> SignalAggregate:
    if not positions:
        return _empty()
    critical_non_forced = sum(1 for p in positions if p.is_critical and not p.is_only_move)
    fraction = critical_non_forced / len(positions)
    return SignalAggregate(
        signal_name=__signal_name__,
        signal_version=__signal_version__,
        mean=fraction,
        weighted_mean=fraction,
        samples=len(positions),
    )


def _empty() -> SignalAggregate:
    return SignalAggregate(
        signal_name=__signal_name__,
        signal_version=__signal_version__,
        mean=0.0,
        weighted_mean=0.0,
        samples=0,
    )
