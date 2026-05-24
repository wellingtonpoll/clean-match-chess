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
__signal_version__ = "2.0.0"

# FR-004 thresholds (T020).
_COMPLEXITY_THRESHOLD = 0.6
_BLUNDER_CANDIDATE_DELTA_CP = -200
_BLUNDER_EVADED_DELTA_CP = -100


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
    moves: tuple[Move, ...] | None = None,
) -> SignalAggregate:
    """Delta-based blunder-suppression signal (FR-004, T020).

    Per FR-004: an "expected blunder position" is one where
    ``complexity.composite > 0.6`` AND at least one candidate in
    ``top_moves[1:]`` has a relative eval delta ≤ -200 cp (i.e., the
    second-or-worse line loses ≥ 2 pawns). "Evaded" means the move
    actually played had ``eval_delta_cp > -100``.

    Silences (samples=0) when no qualifying position exists OR when
    ``moves`` is not supplied (legacy callers pre-T021 — must migrate).
    """
    signal_name = f"{__signal_name__}/blunder-suppression"
    if moves is None:
        return SignalAggregate(
            signal_name=signal_name,
            signal_version=__signal_version__,
            mean=0.0,
            weighted_mean=0.0,
            samples=0,
        )

    expected = 0
    evaded = 0
    for idx in range(min(len(positions), len(moves))):
        pos = positions[idx]
        if pos.complexity is None or pos.complexity.composite <= _COMPLEXITY_THRESHOLD:
            continue
        if pos.eval_cp is None or len(pos.top_moves) < 2:
            continue
        has_blunder = any(
            cand.eval_cp is not None
            and (cand.eval_cp - pos.eval_cp) <= _BLUNDER_CANDIDATE_DELTA_CP
            for cand in pos.top_moves[1:]
        )
        if not has_blunder:
            continue
        expected += 1
        if moves[idx].eval_delta_cp > _BLUNDER_EVADED_DELTA_CP:
            evaded += 1

    if expected == 0:
        return SignalAggregate(
            signal_name=signal_name,
            signal_version=__signal_version__,
            mean=0.0,
            weighted_mean=0.0,
            samples=0,
        )
    value = evaded / expected
    return SignalAggregate(
        signal_name=signal_name,
        signal_version=__signal_version__,
        mean=value,
        weighted_mean=value,
        samples=expected,
    )
