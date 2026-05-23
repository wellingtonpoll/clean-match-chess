"""Suspicion-score aggregation + bootstrap CI (FR-011).

Weights live in `WEIGHTS` so a single deterministic source produces the
final score. Bootstrap CI samples per-signal contributions with
replacement N times.
"""

from __future__ import annotations

import random
from typing import Final

from shared_types.score import RiskLevel, SuspicionScore, risk_level_for
from shared_types.signal import SignalAggregate

from heuristics.scoring.thresholds import SCORING_THRESHOLDS_VERSION

BOOTSTRAP_SAMPLES_DEFAULT: Final[int] = 1000

WEIGHTS: Final[dict[str, float]] = {
    "engine-correlation/weighted": 0.50,
    "engine-correlation/top1": 0.15,
    "engine-correlation/top3": 0.05,
    "regime-shift": 0.10,
    "tactical-detection": 0.05,
    "complexity-analysis": 0.05,
    "behavioral-patterns/precision-burst": 0.05,
    "behavioral-patterns/blunder-suppression": 0.03,
    "timing-analysis": 0.02,
}


def aggregate_score(
    signals: tuple[SignalAggregate, ...],
    *,
    bootstrap_samples: int = BOOTSTRAP_SAMPLES_DEFAULT,
    seed: int = 0,
) -> SuspicionScore:
    by_name = {s.signal_name: s for s in signals}
    weighted_sum = 0.0
    total_weight = 0.0
    contributions: list[tuple[float, float]] = []

    for name, weight in WEIGHTS.items():
        sig = by_name.get(name)
        if sig is None or sig.samples == 0:
            continue
        value = max(0.0, min(1.0, sig.mean))
        weighted_sum += weight * value
        total_weight += weight
        contributions.append((weight, value))

    score = (weighted_sum / total_weight) if total_weight > 0 else 0.0
    score = max(0.0, min(1.0, score))

    ci_low, ci_high = _bootstrap_ci(contributions, samples=bootstrap_samples, seed=seed)

    dominant = _dominant(by_name)

    return SuspicionScore(
        score=score,
        risk_level=risk_level_for(score),
        confidence_interval=(ci_low, ci_high),
        bootstrap_samples=bootstrap_samples,
        dominant_signals=dominant,
    )


def _bootstrap_ci(
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
    names = list(WEIGHTS.keys())
    impact = []
    for name in names:
        weight = WEIGHTS[name]
        sig = by_name.get(name)
        if sig is None or sig.samples == 0:
            continue
        impact.append((name, weight * max(0.0, min(1.0, sig.mean))))
    impact.sort(key=lambda kv: kv[1], reverse=True)
    return tuple(name for name, _ in impact[:3])


def thresholds_version() -> str:
    return SCORING_THRESHOLDS_VERSION


__all__ = [
    "BOOTSTRAP_SAMPLES_DEFAULT",
    "WEIGHTS",
    "RiskLevel",
    "aggregate_score",
    "thresholds_version",
]
