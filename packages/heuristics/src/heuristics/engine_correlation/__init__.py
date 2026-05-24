"""Engine-correlation signal v2 (FR-008, T041, US8).

Computes three SignalAggregates per call: ``top1``, ``top3``,
``weighted``. Each aggregate's ``mean`` holds the raw observed match
rate (back-compat with v1 consumers). When ``baselines`` is supplied,
``weighted_mean`` holds the calibrated ratio ``observed / expected``
from the player's rating bucket (1.0 = matches expectation, >1.0 =
exceeds). The rating-baselines table does not include an expected
top-3 rate, so the ``top3`` aggregate is silenced (samples=0) in
calibrated mode per FR-008.
"""

from __future__ import annotations

from shared_types.game import Move, Position
from shared_types.signal import HeuristicVersion, SignalAggregate

from heuristics.rating_baselines import RatingBaselines

__signal_name__ = "engine-correlation"
__signal_version__ = "2.0.0"


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
    *,
    subject_rating: int | None = None,
    baselines: RatingBaselines | None = None,
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
    weighted_top1 = 0.0
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
            weighted_top1 += complexity

    n = len(eligible)
    top1_rate = top1 / n
    top3_rate = top3 / n
    weighted_rate = (weighted_top1 / total_weight) if total_weight > 0 else 0.0

    if baselines is not None:
        bucket = baselines.bucket_for(subject_rating)
        return (
            _calibrated_agg("engine-correlation/top1", top1_rate, n, bucket.expected_top1),
            # Top-3 expected rate not in baselines → silence.
            _silenced("engine-correlation/top3"),
            _calibrated_agg(
                "engine-correlation/weighted",
                weighted_rate,
                n,
                bucket.expected_weighted_top1,
            ),
        )

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


def _calibrated_agg(
    name: str, observed_rate: float, samples: int, expected_rate: float
) -> SignalAggregate:
    """Calibrated aggregate per FR-008.

    ``mean`` holds the raw observed rate; ``weighted_mean`` holds the
    rating-calibrated ratio (1.0 = matches expectation).
    """
    if expected_rate <= 0.0:
        ratio = 0.0
    else:
        ratio = observed_rate / expected_rate
    return SignalAggregate(
        signal_name=name,
        signal_version=__signal_version__,
        mean=observed_rate,
        weighted_mean=ratio,
        samples=samples,
    )


def _silenced(name: str) -> SignalAggregate:
    return SignalAggregate(
        signal_name=name,
        signal_version=__signal_version__,
        mean=0.0,
        weighted_mean=0.0,
        samples=0,
    )


def _empty() -> SignalAggregate:
    return SignalAggregate(
        signal_name="engine-correlation/empty",
        signal_version=__signal_version__,
        mean=0.0,
        weighted_mean=0.0,
        samples=0,
    )
