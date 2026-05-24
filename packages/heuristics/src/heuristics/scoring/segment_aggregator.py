"""Per-segment heuristic application and phase-weighted aggregation.

Implements `contracts/segment_score.contract.md` (T030, FR-013/014/015).

Public surface: ``aggregate_segments`` returns the segment-weighted game
score AND a tuple of Segments mutated with populated ``signals`` and
``score_contribution``. Game-level-only signals (regime-shift,
precision-burst, complexity, tactical, engine-correlation/top3) are
NOT computed here — the pipeline runs them on the full game and merges
them with the segment-weighted score via ``aggregate_score``.
"""

from __future__ import annotations

from typing import Final

import numpy as np
from shared_types.game import Move, PlayerColor, Position
from shared_types.signal import Phase, Segment, SignalAggregate

from heuristics.acpl_analysis import acpl_signal
from heuristics.behavioral_patterns import blunder_suppression
from heuristics.engine_correlation import engine_correlation
from heuristics.rating_baselines import RatingBaseline, RatingBaselines
from heuristics.scoring.aggregator import WEIGHTS
from heuristics.timing_analysis import timing_anomaly

PHASE_WEIGHTS: Final[dict[Phase, float]] = {
    Phase.OPENING: 0.5,
    Phase.MIDDLEGAME: 1.0,
    Phase.TACTICAL: 1.5,
    Phase.CONVERSION: 1.3,
    Phase.ENDGAME: 0.7,
}

# Subset of WEIGHTS keys that segment_aggregator emits per segment.
_PER_SEGMENT_KEYS: Final[tuple[str, ...]] = (
    "acpl-analysis",
    "engine-correlation/weighted",
    "engine-correlation/top1",
    "behavioral-patterns/blunder-suppression",
    "timing-analysis",
)

# Minimum fraction of moves with timing data before timing-analysis fires
# per segment (per contract).
_TIMING_COVERAGE_THRESHOLD: Final[float] = 0.5


def aggregate_segments(
    segments: tuple[Segment, ...],
    *,
    positions: tuple[Position, ...],
    moves: tuple[Move, ...],
    baselines: RatingBaselines,
    subject_rating: int | None,
    subject_color: PlayerColor,
) -> tuple[float, tuple[Segment, ...]]:
    """Return (game_score, populated_segments) per the contract.

    ``game_score`` is the phase-weighted mean of per-segment raw aggregates.
    ``populated_segments`` is the input tuple with each Segment replaced
    by a copy that has ``signals`` and ``score_contribution`` filled in.
    """
    if not segments:
        return 0.0, ()

    bucket = baselines.bucket_for(subject_rating)

    per_segment_raw: list[float] = []
    per_segment_signals: list[tuple[SignalAggregate, ...]] = []

    for seg in segments:
        sub_positions, sub_moves = _slice_for_segment(seg, positions, moves)
        sigs = _per_segment_signals(
            sub_positions=sub_positions,
            sub_moves=sub_moves,
            subject_color=subject_color,
            subject_rating=subject_rating,
            baselines=baselines,
            bucket=bucket,
        )
        raw = _renormalized_aggregate(sigs)
        per_segment_signals.append(sigs)
        per_segment_raw.append(raw)

    total_phase_weight = sum(PHASE_WEIGHTS[seg.phase] for seg in segments)
    if total_phase_weight <= 0:
        return 0.0, segments

    contributions: list[float] = []
    for seg, raw in zip(segments, per_segment_raw, strict=True):
        contribution = PHASE_WEIGHTS[seg.phase] * raw / total_phase_weight
        contributions.append(contribution)

    game_score = float(np.clip(sum(contributions), 0.0, 1.0))

    populated = tuple(
        seg.model_copy(
            update={
                "signals": sigs,
                "score_contribution": float(np.clip(contribution, 0.0, 1.0)),
            }
        )
        for seg, sigs, contribution in zip(
            segments, per_segment_signals, contributions, strict=True
        )
    )
    return game_score, populated


def _slice_for_segment(
    segment: Segment,
    positions: tuple[Position, ...],
    moves: tuple[Move, ...],
) -> tuple[tuple[Position, ...], tuple[Move, ...]]:
    start, end = segment.ply_range
    end = min(end, len(positions), len(moves))
    start = max(0, min(start, end))
    return positions[start:end], moves[start:end]


def _per_segment_signals(
    *,
    sub_positions: tuple[Position, ...],
    sub_moves: tuple[Move, ...],
    subject_color: PlayerColor,
    subject_rating: int | None,
    baselines: RatingBaselines,
    bucket: RatingBaseline,
) -> tuple[SignalAggregate, ...]:
    if not sub_positions or not sub_moves:
        return ()

    acpl = acpl_signal(
        positions=sub_positions,
        moves=sub_moves,
        subject_color=subject_color,
        subject_rating=subject_rating,
        baselines=baselines,
    )
    top1, _top3, weighted = engine_correlation(sub_positions, sub_moves)
    bs = blunder_suppression(sub_positions, sub_moves)

    top1_norm = _normalize_engine_correlation_rate(top1, bucket.expected_top1)
    weighted_norm = _normalize_engine_correlation_rate(weighted, bucket.expected_weighted_top1)

    signals: list[SignalAggregate] = [acpl, top1_norm, weighted_norm, bs]

    timed = sum(1 for m in sub_moves if m.time_spent_ms is not None)
    if timed >= max(1, int(len(sub_moves) * _TIMING_COVERAGE_THRESHOLD)):
        signals.append(timing_anomaly(sub_positions, sub_moves))

    return tuple(signals)


def _normalize_engine_correlation_rate(
    sig: SignalAggregate,
    expected_rate: float,
) -> SignalAggregate:
    """Apply piecewise linear mapping (contract §Normalization)."""
    if sig.samples == 0 or expected_rate <= 0.0:
        return sig
    ratio = sig.mean / expected_rate
    score = float(np.clip((ratio - 1.0) / 1.5, 0.0, 1.0))
    return sig.model_copy(update={"mean": score, "weighted_mean": score})


def _renormalized_aggregate(signals: tuple[SignalAggregate, ...]) -> float:
    """Per-segment raw aggregate per contract §Per-segment aggregation."""
    total = 0.0
    weight_sum = 0.0
    for s in signals:
        if s.samples == 0:
            continue
        weight = WEIGHTS.get(s.signal_name, 0.0)
        if weight <= 0:
            continue
        total += weight * float(np.clip(s.mean, 0.0, 1.0))
        weight_sum += weight
    if weight_sum <= 0:
        return 0.0
    return float(np.clip(total / weight_sum, 0.0, 1.0))


__all__ = [
    "PHASE_WEIGHTS",
    "aggregate_segments",
]
