"""Engine-correlation signal (FR-008, FR-009).

Computes three aggregates:
- top-1 match rate (player's move == engine top move)
- top-3 match rate
- complexity-weighted top-1 (matches in high-complexity positions count
  more, per constitution Principle 7)

For MVP the comparison uses the played UCI string vs `Position.top_moves`.
Book and forced-move plies are excluded from the denominator
(Principles 5 + 6).
"""

from __future__ import annotations

from shared_types.game import Move, Position
from shared_types.signal import HeuristicVersion, SignalAggregate

__signal_name__ = "engine-correlation"
__signal_version__ = "0.1.0"


def signal_version() -> HeuristicVersion:
    return HeuristicVersion(
        name=__signal_name__,
        version=__signal_version__,
        git_sha="0000000",
        owner="cleanmatch",
        changelog_path="packages/heuristics/CHANGELOG.md",
    )


def engine_correlation(
    positions: tuple[Position, ...],
    moves: tuple[Move, ...],
) -> tuple[SignalAggregate, SignalAggregate, SignalAggregate]:
    eligible = [
        (pos, moves[idx])
        for idx, pos in enumerate(positions)
        if idx < len(moves) and _is_eligible(pos)
    ]
    if not eligible:
        z = _empty()
        return z, z, z

    top1 = 0
    top3 = 0
    weighted = 0.0
    total_weight = 0.0
    for pos, mv in eligible:
        top_ucis = [c.uci for c in pos.top_moves[:3]]
        if not top_ucis:
            continue
        if mv.uci == top_ucis[0]:
            top1 += 1
        if mv.uci in top_ucis:
            top3 += 1
        complexity = pos.complexity.composite if pos.complexity else 0.0
        total_weight += complexity
        if mv.uci == top_ucis[0]:
            weighted += complexity

    n = len(eligible)
    top1_rate = top1 / n
    top3_rate = top3 / n
    weighted_rate = (weighted / total_weight) if total_weight > 0 else 0.0

    return (
        _agg("engine-correlation/top1", top1_rate, n),
        _agg("engine-correlation/top3", top3_rate, n),
        _agg("engine-correlation/weighted", weighted_rate, n),
    )


def _is_eligible(position: Position) -> bool:
    return not position.is_book and not position.is_only_move


def _agg(name: str, value: float, samples: int) -> SignalAggregate:
    return SignalAggregate(
        signal_name=name,
        signal_version=__signal_version__,
        mean=value,
        weighted_mean=value,
        samples=samples,
    )


def _empty() -> SignalAggregate:
    return SignalAggregate(
        signal_name="engine-correlation/empty",
        signal_version=__signal_version__,
        mean=0.0,
        weighted_mean=0.0,
        samples=0,
    )
