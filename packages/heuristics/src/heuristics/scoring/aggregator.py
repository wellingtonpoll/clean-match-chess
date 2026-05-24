"""Suspicion-score aggregation + bootstrap CI (FR-007, FR-016).

Weights live in `WEIGHTS` so a single deterministic source produces the
final score. The Phase 1 (feature 004) bootstrap is move-resampling: per
resample, pick N plies with replacement, recompute every heuristic via
the caller-supplied `resample_signals` closure, then aggregate. The
legacy contribution-bootstrap is retained behind a DeprecationWarning
for callers that have not yet migrated.

The Phase 1 weights add the new `acpl-analysis` signal at 0.30 and
reduce `engine-correlation/top1` from 0.15 to 0.05; the full
distribution is specified by FR-016 and must sum to exactly 1.0.
"""

from __future__ import annotations

import random
import warnings
from collections.abc import Callable
from typing import Final

import numpy as np
from shared_types.game import Move, Position
from shared_types.score import RiskLevel, SuspicionScore, risk_level_for
from shared_types.signal import SignalAggregate

from heuristics.scoring.thresholds import SCORING_THRESHOLDS_VERSION

BOOTSTRAP_SAMPLES_DEFAULT: Final[int] = 10000

# Below this ply count the move-resampling bootstrap returns the widest
# permissible interval rather than a misleadingly narrow one (US3 edge
# case from spec.md).
_BOOTSTRAP_DEGENERATE_THRESHOLD: Final[int] = 5

ResampleSignalsFn = Callable[
    [tuple[Position, ...], tuple[Move, ...]],
    tuple[SignalAggregate, ...],
]

# Phase 1 (feature 004) FR-016 distribution. The per-signal keys
# sum to 1.0 exactly. ``segments-weighted-aggregate`` is the carrier the
# pipeline uses when it has already phase-weighted the per-segment
# signals via ``segment_aggregator.aggregate_segments`` — its weight is
# the SUM of the per-segment-applicable signal weights (acpl=0.30,
# engine-correlation/weighted=0.30, engine-correlation/top1=0.05,
# blunder-suppression=0.05, timing-analysis=0.04 → 0.74). The aggregator
# renormalises over the SUBSET of signals actually present, so the
# WEIGHTS sum may exceed 1.0 — the weighted MEAN is still in [0, 1].
WEIGHTS: Final[dict[str, float]] = {
    "acpl-analysis": 0.30,
    "engine-correlation/weighted": 0.30,
    "engine-correlation/top1": 0.05,
    "engine-correlation/top3": 0.05,
    "regime-shift": 0.10,
    "tactical-detection": 0.03,
    "complexity-analysis": 0.03,
    "behavioral-patterns/precision-burst": 0.05,
    "behavioral-patterns/blunder-suppression": 0.05,
    "timing-analysis": 0.04,
    "segments-weighted-aggregate": 0.74,
}


def aggregate_score(
    signals: tuple[SignalAggregate, ...],
    *,
    positions: tuple[Position, ...] | None = None,
    moves: tuple[Move, ...] | None = None,
    bootstrap_samples: int = BOOTSTRAP_SAMPLES_DEFAULT,
    seed: int = 0,
    resample_signals: ResampleSignalsFn | None = None,
) -> SuspicionScore:
    """Aggregate per-signal SignalAggregates into a single SuspicionScore.

    The score is the weighted mean of in-scope signal means. The CI is:
      * Move-resampling bootstrap (FR-007) when ``positions``, ``moves``,
        and ``resample_signals`` are all supplied.
      * Otherwise the legacy contribution bootstrap (with
        DeprecationWarning) — kept for tests and pre-migration callers.
    """
    score, contributions, by_name = _compute_score(signals)

    if positions is not None and moves is not None and resample_signals is not None:
        ci_low, ci_high = _move_resample_ci(
            positions=positions,
            moves=moves,
            samples=bootstrap_samples,
            seed=seed,
            resample_signals=resample_signals,
        )
    else:
        if positions is not None or moves is not None or resample_signals is not None:
            # Partial inputs: caller is mid-migration. Treat as legacy.
            warnings.warn(
                "aggregate_score(): partial move-resampling inputs; "
                "falling back to legacy contribution-bootstrap.",
                DeprecationWarning,
                stacklevel=2,
            )
        ci_low, ci_high = _contribution_ci(contributions, samples=bootstrap_samples, seed=seed)

    dominant = _dominant(by_name)

    return SuspicionScore(
        score=score,
        risk_level=risk_level_for(score),
        confidence_interval=(ci_low, ci_high),
        bootstrap_samples=bootstrap_samples,
        dominant_signals=dominant,
    )


def ratio_to_score(ratio: float) -> float:
    """Piecewise linear FR-008 normalization: ratio → suspicion score.

    ratio 1.0 → 0.0 (matches baseline; no suspicion contribution)
    ratio 2.5 → 1.0 (maximum suspicion)
    ratio < 1.0 → 0.0 (clamped; below-expectation play not penalized)
    """
    return float(np.clip((ratio - 1.0) / 1.5, 0.0, 1.0))


def _compute_score(
    signals: tuple[SignalAggregate, ...],
) -> tuple[float, list[tuple[float, float]], dict[str, SignalAggregate]]:
    by_name = {s.signal_name: s for s in signals}
    weighted_sum = 0.0
    total_weight = 0.0
    contributions: list[tuple[float, float]] = []
    for name, weight in WEIGHTS.items():
        sig = by_name.get(name)
        if sig is None or sig.samples == 0:
            continue
        value = _value_for_signal(sig)
        weighted_sum += weight * value
        total_weight += weight
        contributions.append((weight, value))
    score = (weighted_sum / total_weight) if total_weight > 0 else 0.0
    return max(0.0, min(1.0, score)), contributions, by_name


def _value_for_signal(sig: SignalAggregate) -> float:
    """Return the [0,1] contribution value for a signal (T043, FR-008).

    Calibrated engine-correlation signals carry the observed rate in
    ``mean`` and the rating-bucket ratio in ``weighted_mean``. Normalize
    the ratio via ``ratio_to_score``. Other signals use ``mean`` clamped
    to [0, 1].
    """
    if sig.signal_name.startswith("engine-correlation/") and sig.weighted_mean != sig.mean:
        return ratio_to_score(sig.weighted_mean)
    return max(0.0, min(1.0, sig.mean))


def _move_resample_ci(
    *,
    positions: tuple[Position, ...],
    moves: tuple[Move, ...],
    samples: int,
    seed: int,
    resample_signals: ResampleSignalsFn,
) -> tuple[float, float]:
    n = min(len(positions), len(moves))
    if n < _BOOTSTRAP_DEGENERATE_THRESHOLD:
        return (0.0, 1.0)

    rng = np.random.default_rng(seed)
    pos_arr = positions[:n]
    mov_arr = moves[:n]
    # Pre-allocate the index batch as one int32 array. Resampling 10000x
    # one-at-a-time is the dominant cost; batched generation halves it.
    all_indices = rng.integers(0, n, size=(samples, n))

    draws: list[float] = []
    for s_idx in range(samples):
        idx = all_indices[s_idx]
        resampled_positions = tuple(pos_arr[i] for i in idx)
        resampled_moves = tuple(mov_arr[i] for i in idx)
        sub_signals = resample_signals(resampled_positions, resampled_moves)
        if not sub_signals or all(s.samples == 0 for s in sub_signals):
            draws.append(0.0)
            continue
        sub_score, _, _ = _compute_score(sub_signals)
        draws.append(sub_score)

    if not draws:
        return (0.0, 1.0)
    arr = np.sort(np.asarray(draws, dtype=float))
    lo = float(arr[int(0.025 * (len(arr) - 1))])
    hi = float(arr[int(0.975 * (len(arr) - 1))])
    return (lo, hi)


def _contribution_ci(
    contributions: list[tuple[float, float]],
    *,
    samples: int,
    seed: int,
) -> tuple[float, float]:
    if not contributions:
        return (0.0, 0.0)
    rng = random.Random(seed)  # noqa: S311  bootstrap CI, not security
    weights = [c[0] for c in contributions]
    values = [c[1] for c in contributions]
    total_weight = sum(weights)
    if total_weight <= 0:
        return (0.0, 0.0)
    draws: list[float] = []
    n = len(contributions)
    for _ in range(samples):
        wsum = 0.0
        vsum = 0.0
        for _i in range(n):
            idx = rng.randrange(n)
            wsum += weights[idx]
            vsum += weights[idx] * values[idx]
        if wsum > 0:
            draws.append(max(0.0, min(1.0, vsum / wsum)))
    if not draws:
        return (0.0, 0.0)
    draws.sort()
    lo = draws[int(0.025 * (len(draws) - 1))]
    hi = draws[int(0.975 * (len(draws) - 1))]
    return (lo, hi)


def _dominant(by_name: dict[str, SignalAggregate]) -> tuple[str, ...]:
    impact = []
    for name in WEIGHTS:
        weight = WEIGHTS[name]
        sig = by_name.get(name)
        if sig is None or sig.samples == 0:
            continue
        impact.append((name, weight * _value_for_signal(sig)))
    impact.sort(key=lambda kv: kv[1], reverse=True)
    return tuple(name for name, _ in impact[:3])


def thresholds_version() -> str:
    return SCORING_THRESHOLDS_VERSION


__all__ = [
    "BOOTSTRAP_SAMPLES_DEFAULT",
    "WEIGHTS",
    "ResampleSignalsFn",
    "RiskLevel",
    "aggregate_score",
    "ratio_to_score",
    "thresholds_version",
]
