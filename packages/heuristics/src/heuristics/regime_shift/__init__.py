"""Regime-shift signal v2 (FR-005, T038, US7).

CUSUM change-point detection over the per-move ACPL series. Detects
sudden quality shifts (e.g., a player switching to engine assistance
mid-game) that the v1 segment-size heuristic could not see.

Algorithm: running mean and stdev of cp-loss; CUSUM accumulators S+/S-
with threshold ``k_sigma x running_stdev``. Crossing the threshold
flags a change-point and resets the accumulators. The signal value is
``min(1.0, change_points / 3.0)`` so 0 change points → 0.0 and ≥ 3 →
1.0.

API: ``regime_shift_score`` accepts either the legacy ``segments``
argument (returns 0-sample silenced aggregate — segment-size variation
is no longer the metric) OR ``(positions, moves)`` with optional
``k_sigma`` per the new contract.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from shared_types.game import Move, Position
from shared_types.signal import HeuristicVersion, Segment, SignalAggregate

__signal_name__ = "regime-shift"
__signal_version__ = "2.0.0"

_MIN_PLIES = 10
_DEFAULT_K_SIGMA = 4.0
# Classic CUSUM uses a "slack" K (small) and a detection threshold H
# (large). Research R5 names the detection threshold ``k=4sigma`` directly,
# so K is set to a small fraction of sigma to absorb stationary noise drift.
_SLACK_FRACTION = 1.5


def signal_version() -> HeuristicVersion:
    return HeuristicVersion(
        name=__signal_name__,
        version=__signal_version__,
        git_sha="0000000",
        owner="cleanmatch",
        changelog_path="packages/heuristics/CHANGELOG.md",
    )


def regime_shift_score(
    arg: tuple[Segment, ...] | tuple[Position, ...],
    moves: tuple[Move, ...] | None = None,
    *,
    k_sigma: float = _DEFAULT_K_SIGMA,
) -> SignalAggregate:
    """CUSUM on ACPL series.

    Backwards-compatible signature: when called as
    ``regime_shift_score(segments)`` (no ``moves``), returns a silenced
    aggregate — segment-size variation is the v1 algorithm and is no
    longer scored. When called as
    ``regime_shift_score(positions, moves)`` runs CUSUM.
    """
    if moves is None:
        # Legacy call site (segments-only) — silence.
        return _silenced(samples=0)

    positions = arg
    series = _acpl_series(positions, moves)  # type: ignore[arg-type]
    if len(series) < _MIN_PLIES:
        return _silenced(samples=0)

    change_points = _cusum_change_points(series, k_sigma=k_sigma)
    value = float(np.clip(len(change_points) / 3.0, 0.0, 1.0))
    return SignalAggregate(
        signal_name=__signal_name__,
        signal_version=__signal_version__,
        mean=value,
        weighted_mean=value,
        samples=len(series),
    )


def _acpl_series(
    positions: tuple[Position, ...],
    moves: tuple[Move, ...],
) -> list[float]:
    """Per-move cp-loss series, restricted to non-book plies."""
    out: list[float] = []
    n = min(len(positions), len(moves))
    for i in range(n):
        pos = positions[i]
        if pos.is_book:
            continue
        loss = max(0.0, -float(moves[i].eval_delta_cp))
        out.append(loss)
    return out


def _cusum_change_points(
    series: Iterable[float],
    *,
    k_sigma: float,
) -> list[int]:
    """Two-sided CUSUM. Returns indices where the accumulator exceeds kxsigma."""
    arr = np.asarray(list(series), dtype=float)
    n = len(arr)
    if n < _MIN_PLIES:
        return []

    # Page CUSUM with reference value = mean of an initial warm-up
    # window. Computing the reference from a prefix (rather than the
    # full series) is what lets the detector see a step change: a global
    # mean would sit between the two regimes and mask the shift.
    warmup = max(_MIN_PLIES, n // 6)
    warmup = min(warmup, n)
    ref_mean = float(np.mean(arr[:warmup]))
    stdev = float(np.std(arr))
    if stdev == 0.0:
        return []

    threshold = k_sigma * stdev
    slack = _SLACK_FRACTION * stdev
    cusum_pos = 0.0
    cusum_neg = 0.0
    points: list[int] = []
    for i, x in enumerate(arr):
        delta = x - ref_mean
        cusum_pos = max(0.0, cusum_pos + delta - slack)
        cusum_neg = min(0.0, cusum_neg + delta + slack)
        if cusum_pos > threshold:
            points.append(i)
            cusum_pos = 0.0
            cusum_neg = 0.0
        elif -cusum_neg > threshold:
            points.append(i)
            cusum_pos = 0.0
            cusum_neg = 0.0
    return points


def _silenced(samples: int) -> SignalAggregate:
    return SignalAggregate(
        signal_name=__signal_name__,
        signal_version=__signal_version__,
        mean=0.0,
        weighted_mean=0.0,
        samples=samples,
    )
