"""AccountProfile aggregation + cross-game patterns (T063)."""

from __future__ import annotations

from heuristics.scoring.account_profile import (
    PATTERN_SUPPORT_THRESHOLD,
    build_account_profile,
)
from shared_types.score import RiskLevel, SuspicionScore


def _score(value: float, dominant: tuple[str, ...] = ()) -> SuspicionScore:
    from shared_types.score import risk_level_for

    return SuspicionScore(
        score=value,
        risk_level=risk_level_for(value),
        confidence_interval=(max(0.0, value - 0.05), min(1.0, value + 0.05)),
        dominant_signals=dominant,
    )


def test_empty_run_set_yields_empty_profile() -> None:
    p = build_account_profile("alice", ())
    assert p.games_audited == 0
    assert p.aggregate_score.score == 0.0
    assert p.aggregate_score.risk_level is RiskLevel.LOW
    assert p.cross_game_patterns == ()


def test_aggregate_uses_arithmetic_mean() -> None:
    p = build_account_profile("alice", (_score(0.2), _score(0.4), _score(0.6)))
    assert abs(p.aggregate_score.score - 0.4) < 1e-9


def test_ci_envelopes_extremes() -> None:
    p = build_account_profile("alice", (_score(0.2), _score(0.8)))
    lo, hi = p.aggregate_score.confidence_interval
    assert lo <= 0.2
    assert hi >= 0.8


def test_pattern_emitted_when_signal_dominates_majority() -> None:
    scores = (
        _score(0.5, ("engine-correlation/weighted",)),
        _score(0.5, ("engine-correlation/weighted",)),
        _score(0.5, ("regime-shift",)),
    )
    p = build_account_profile("alice", scores, run_ids=("r1", "r2", "r3"))
    pattern_names = {pat.name for pat in p.cross_game_patterns}
    assert "engine-correlation/weighted" in pattern_names


def test_pattern_threshold_filters_low_support() -> None:
    scores = tuple(_score(0.5, ("rare-signal",)) if i == 0 else _score(0.5) for i in range(10))
    p = build_account_profile("alice", scores)
    pattern_names = {pat.name for pat in p.cross_game_patterns}
    assert "rare-signal" not in pattern_names
    assert 1 / 10 < PATTERN_SUPPORT_THRESHOLD
