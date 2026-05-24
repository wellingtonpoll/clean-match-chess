"""Timing-analysis signal v2 (FR-006, T035, US6).

Regression-residual model of move time on (complexity, phase). The
signal value is the fraction of moves whose log-time residual exceeds
±2sigma, blended with the fraction of non-trivial positions played in
under 300ms ("pre-moves").

Math: ``log(time_ms + 1) ~ β_c · complexity + β_p · phase_ordinal + alpha``
fit via OLS (``numpy.linalg.lstsq``). Phase ordinals: OPENING=0,
MIDDLEGAME=1, TACTICAL=2, CONVERSION=3, ENDGAME=4. When phase ordinals
are not supplied (callers pre-T036) the regression uses complexity only.
The signal silences (samples=0) when fewer than ``_MIN_TIMED`` moves
have ``time_spent_ms`` populated.
"""

from __future__ import annotations

import math

import numpy as np
from shared_types.game import Move, Position
from shared_types.signal import HeuristicVersion, SignalAggregate

__signal_name__ = "timing-analysis"
__signal_version__ = "2.0.0"

_MIN_TIMED = 10
_PREMOVE_MS_THRESHOLD = 300
_PREMOVE_COMPLEXITY_THRESHOLD = 0.2
_RESIDUAL_SIGMA_THRESHOLD = 2.0
_RESIDUAL_WEIGHT = 0.7
_PREMOVE_WEIGHT = 0.3


def signal_version() -> HeuristicVersion:
    return HeuristicVersion(
        name=__signal_name__,
        version=__signal_version__,
        git_sha="0000000",
        owner="cleanmatch",
        changelog_path="packages/heuristics/CHANGELOG.md",
    )


def timing_anomaly(
    positions: tuple[Position, ...],
    moves: tuple[Move, ...],
    *,
    phase_ordinals: tuple[int, ...] | None = None,
) -> SignalAggregate:
    n = min(len(positions), len(moves))
    eligible_idx = [
        i
        for i in range(n)
        if moves[i].time_spent_ms is not None and positions[i].complexity is not None
    ]
    if len(eligible_idx) < _MIN_TIMED:
        return _silenced()

    complexity_scores = np.asarray(
        [
            positions[i].complexity.composite  # type: ignore[union-attr]
            for i in eligible_idx
        ],
        dtype=np.float64,
    )
    times_ms = np.asarray([moves[i].time_spent_ms for i in eligible_idx], dtype=np.float64)
    log_times = np.log(times_ms + 1.0)

    if phase_ordinals is not None and len(phase_ordinals) >= n:
        phases = np.asarray([phase_ordinals[i] for i in eligible_idx], dtype=np.float64)
        features = np.column_stack([complexity_scores, phases])
    else:
        features = complexity_scores.reshape(-1, 1)

    bias = np.ones(len(eligible_idx), dtype=np.float64)
    design = np.column_stack([features, bias])
    coeffs, _residuals, _rank, _sv = np.linalg.lstsq(design, log_times, rcond=None)
    predicted = design @ coeffs
    residuals = log_times - predicted
    stdev = float(np.std(residuals))
    if stdev == 0 or not math.isfinite(stdev):
        residual_rate = 0.0
    else:
        anomalies = np.sum(np.abs(residuals) > _RESIDUAL_SIGMA_THRESHOLD * stdev)
        residual_rate = float(anomalies / len(eligible_idx))

    premove_eligible = [
        i
        for i in eligible_idx
        if positions[i].complexity is not None
        and positions[i].complexity.composite > _PREMOVE_COMPLEXITY_THRESHOLD  # type: ignore[union-attr]
    ]
    if not premove_eligible:
        premove_rate = 0.0
    else:
        premoves = sum(
            1 for i in premove_eligible if (moves[i].time_spent_ms or 0) < _PREMOVE_MS_THRESHOLD
        )
        premove_rate = premoves / len(premove_eligible)

    value = float(
        np.clip(
            _RESIDUAL_WEIGHT * residual_rate + _PREMOVE_WEIGHT * premove_rate,
            0.0,
            1.0,
        )
    )
    return SignalAggregate(
        signal_name=__signal_name__,
        signal_version=__signal_version__,
        mean=value,
        weighted_mean=value,
        samples=len(eligible_idx),
    )


def _silenced() -> SignalAggregate:
    return SignalAggregate(
        signal_name=__signal_name__,
        signal_version=__signal_version__,
        mean=0.0,
        weighted_mean=0.0,
        samples=0,
    )
