"""ACPL signal (T015, FR-002, FR-003).

Computes a rating-bucket-calibrated Average Centipawn Loss suspicion
score for one game. See `specs/004-scoring-v2-phase1/contracts/
acpl_signal.contract.md` for the full eligibility + silencing
specification.

Public API:

    acpl_signal(positions, moves, subject_color, subject_rating, baselines)
        -> SignalAggregate
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Final

from shared_types.game import Move, PlayerColor, Position
from shared_types.signal import HeuristicVersion, SignalAggregate

from heuristics.rating_baselines import RatingBaseline, RatingBaselines

__signal_name__: Final[str] = "acpl-analysis"
__signal_version__: Final[str] = "1.0.0"

MIN_ELIGIBLE_PLIES: Final[int] = 10


@dataclass(frozen=True, slots=True)
class AcplStats:
    """Internal computation type returned by `_compute()`."""

    observed_mean: float
    observed_stdev: float
    sample_count: int
    expected_mean: float
    expected_stdev: float
    rating_bucket_label: str
    suspicion_value: float


def signal_version() -> HeuristicVersion:
    return HeuristicVersion(
        name=__signal_name__,
        version=__signal_version__,
        git_sha="0000000",
        owner="cleanmatch",
        changelog_path="packages/heuristics/CHANGELOG.md",
    )


def acpl_signal(
    positions: tuple[Position, ...],
    moves: tuple[Move, ...],
    subject_color: PlayerColor,
    subject_rating: int | None,
    baselines: RatingBaselines,
) -> SignalAggregate:
    """Compute the rating-calibrated ACPL suspicion signal.

    Silenced (samples=0, mean=0.0) when fewer than 10 eligible non-book
    non-only-move plies are available. The aggregator skips silenced
    signals — it does not count them against `total_weight`.
    """
    bucket = baselines.bucket_for(subject_rating)
    eligible_losses = _collect_losses(positions, moves, subject_color)

    if len(eligible_losses) < MIN_ELIGIBLE_PLIES:
        return _silenced()

    stats = _compute_stats(eligible_losses, bucket)
    return SignalAggregate(
        signal_name=__signal_name__,
        signal_version=__signal_version__,
        mean=stats.suspicion_value,
        weighted_mean=stats.suspicion_value,
        samples=stats.sample_count,
    )


def _collect_losses(
    positions: tuple[Position, ...],
    moves: tuple[Move, ...],
    subject_color: PlayerColor,
) -> list[float]:
    losses: list[float] = []
    for idx, mv in enumerate(moves):
        if idx >= len(positions):
            break
        pos = positions[idx]
        if pos.is_book:
            continue
        if pos.is_only_move:
            continue
        if mv.played_by != subject_color:
            continue
        if mv.eval_delta_cp is None:
            continue
        loss = max(0, -int(mv.eval_delta_cp))
        losses.append(float(loss))
    return losses


def _compute_stats(losses: list[float], bucket: RatingBaseline) -> AcplStats:
    observed_mean = statistics.fmean(losses)
    observed_stdev = statistics.pstdev(losses) if len(losses) > 1 else 0.0
    expected_stdev = bucket.expected_acpl_stdev
    if expected_stdev <= 0.0:
        suspicion = 0.0
    else:
        z = (bucket.expected_acpl_mean - observed_mean) / expected_stdev
        suspicion = max(0.0, min(1.0, z / 3.0))
    return AcplStats(
        observed_mean=observed_mean,
        observed_stdev=observed_stdev,
        sample_count=len(losses),
        expected_mean=bucket.expected_acpl_mean,
        expected_stdev=expected_stdev,
        rating_bucket_label=bucket.bucket_label,
        suspicion_value=suspicion,
    )


def _silenced() -> SignalAggregate:
    return SignalAggregate(
        signal_name=__signal_name__,
        signal_version=__signal_version__,
        mean=0.0,
        weighted_mean=0.0,
        samples=0,
    )


__all__ = [
    "MIN_ELIGIBLE_PLIES",
    "AcplStats",
    "acpl_signal",
    "signal_version",
]
