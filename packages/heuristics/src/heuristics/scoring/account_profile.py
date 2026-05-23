"""AccountProfile aggregation across multiple per-game runs (T066).

Combines per-game `SuspicionScore`s into one account-level score and
extracts cross-game patterns (e.g., "regime-shift dominated in K of N
games"). The aggregate is intentionally conservative: arithmetic mean
of per-game scores, CI taken as min/max envelope.
"""

from __future__ import annotations

from collections import Counter

from shared_types.audit_run import AccountProfile, CrossGamePattern
from shared_types.score import RiskLevel, SuspicionScore, risk_level_for

PATTERN_SUPPORT_THRESHOLD = 0.30


def build_account_profile(
    username: str,
    per_game_scores: tuple[SuspicionScore, ...],
    *,
    platform: str = "chesscom",
    run_ids: tuple[str, ...] = (),
) -> AccountProfile:
    if not per_game_scores:
        return AccountProfile(
            username=username,
            platform=platform,
            games_audited=0,
            per_game_scores=(),
            aggregate_score=_empty_score(),
            cross_game_patterns=(),
        )

    aggregate = _aggregate(per_game_scores)
    patterns = _cross_game_patterns(per_game_scores, run_ids)
    return AccountProfile(
        username=username,
        platform=platform,
        games_audited=len(per_game_scores),
        per_game_scores=per_game_scores,
        aggregate_score=aggregate,
        cross_game_patterns=patterns,
    )


def _aggregate(scores: tuple[SuspicionScore, ...]) -> SuspicionScore:
    mean_score = sum(s.score for s in scores) / len(scores)
    mean_score = max(0.0, min(1.0, mean_score))
    ci_low = min(s.confidence_interval[0] for s in scores)
    ci_high = max(s.confidence_interval[1] for s in scores)
    dominant_counter: Counter[str] = Counter()
    for s in scores:
        dominant_counter.update(s.dominant_signals)
    dominant = tuple(name for name, _ in dominant_counter.most_common(3))
    return SuspicionScore(
        score=mean_score,
        risk_level=risk_level_for(mean_score),
        confidence_interval=(ci_low, ci_high),
        bootstrap_samples=max(s.bootstrap_samples for s in scores),
        dominant_signals=dominant,
    )


def _cross_game_patterns(
    scores: tuple[SuspicionScore, ...], run_ids: tuple[str, ...]
) -> tuple[CrossGamePattern, ...]:
    counter: Counter[str] = Counter()
    indices: dict[str, list[int]] = {}
    for idx, s in enumerate(scores):
        for name in s.dominant_signals:
            counter[name] += 1
            indices.setdefault(name, []).append(idx)

    total = max(1, len(scores))
    patterns: list[CrossGamePattern] = []
    for name, hits in counter.most_common():
        support = hits / total
        if support < PATTERN_SUPPORT_THRESHOLD:
            continue
        evidence = tuple(run_ids[i] for i in indices[name] if i < len(run_ids))
        patterns.append(
            CrossGamePattern(
                name=name,
                description=f"Signal {name} dominated in {hits}/{total} audited games.",
                support=support,
                evidence_runs=evidence,
            )
        )
    return tuple(patterns)


def _empty_score() -> SuspicionScore:
    return SuspicionScore(
        score=0.0,
        risk_level=RiskLevel.LOW,
        confidence_interval=(0.0, 0.0),
    )
