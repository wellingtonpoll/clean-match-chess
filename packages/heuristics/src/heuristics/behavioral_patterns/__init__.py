"""Behavioral-patterns signal (FR-010).

Approximates two sub-signals:
- bursts of precision: longest streak of consecutive top-1 matches
- blunder suppression: fraction of expected-blunder positions (high
  complexity + large eval swing potential) where no blunder occurred

For MVP these are coarse proxies on the static-analyzer output.
"""

from __future__ import annotations

from shared_types.game import Move, Position
from shared_types.signal import HeuristicVersion, SignalAggregate

__signal_name__ = "behavioral-patterns"
__signal_version__ = "0.1.0"


def signal_version() -> HeuristicVersion:
    return HeuristicVersion(
        name=__signal_name__,
        version=__signal_version__,
        git_sha="0000000",
        owner="cleanmatch",
        changelog_path="packages/heuristics/CHANGELOG.md",
    )


def precision_burst(
    positions: tuple[Position, ...],
    moves: tuple[Move, ...],
) -> SignalAggregate:
    streak = 0
    best = 0
    for idx, pos in enumerate(positions):
        if idx >= len(moves):
            break
        top_uci = pos.top_moves[0].uci if pos.top_moves else None
        if top_uci and moves[idx].uci == top_uci:
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    normalised = min(1.0, best / max(1, len(positions)))
    return SignalAggregate(
        signal_name=f"{__signal_name__}/precision-burst",
        signal_version=__signal_version__,
        mean=normalised,
        weighted_mean=normalised,
        samples=len(positions),
    )


def blunder_suppression(
    positions: tuple[Position, ...],
) -> SignalAggregate:
    expected_blunder = [p for p in positions if p.complexity and p.complexity.composite > 0.7]
    if not expected_blunder:
        return SignalAggregate(
            signal_name=f"{__signal_name__}/blunder-suppression",
            signal_version=__signal_version__,
            mean=0.0,
            weighted_mean=0.0,
            samples=0,
        )
    suppressed = sum(1 for p in expected_blunder if p.eval_cp is not None and abs(p.eval_cp) < 200)
    value = suppressed / len(expected_blunder)
    return SignalAggregate(
        signal_name=f"{__signal_name__}/blunder-suppression",
        signal_version=__signal_version__,
        mean=value,
        weighted_mean=value,
        samples=len(expected_blunder),
    )
