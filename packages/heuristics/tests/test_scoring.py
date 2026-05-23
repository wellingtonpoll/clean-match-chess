"""Scoring aggregator + bootstrap CI (T044)."""

from __future__ import annotations

from heuristics.scoring import aggregate_score
from heuristics.scoring.aggregator import WEIGHTS
from shared_types.score import RiskLevel
from shared_types.signal import SignalAggregate


def _agg(name: str, value: float, samples: int = 10) -> SignalAggregate:
    return SignalAggregate(
        signal_name=name,
        signal_version="0.1.0",
        mean=value,
        weighted_mean=value,
        samples=samples,
    )


def test_empty_signals_produce_low_score() -> None:
    s = aggregate_score(())
    assert s.score == 0.0
    assert s.risk_level is RiskLevel.LOW
    assert s.confidence_interval == (0.0, 0.0)


def test_all_signals_at_one_yields_high_risk() -> None:
    signals = tuple(_agg(name, 1.0) for name in WEIGHTS)
    s = aggregate_score(signals, seed=42)
    assert s.score == 1.0
    assert s.risk_level is RiskLevel.HIGH


def test_only_weighted_correlation_drives_high_risk() -> None:
    signals = (
        _agg("engine-correlation/weighted", 1.0),
        _agg("engine-correlation/top1", 1.0),
        _agg("engine-correlation/top3", 1.0),
    )
    s = aggregate_score(signals, seed=0)
    assert s.score >= 0.7
    assert s.risk_level is RiskLevel.HIGH


def test_bootstrap_seed_determinism() -> None:
    signals = tuple(_agg(name, 0.5) for name in WEIGHTS)
    a = aggregate_score(signals, seed=123)
    b = aggregate_score(signals, seed=123)
    assert a.model_dump() == b.model_dump()


def test_zero_sample_signals_ignored() -> None:
    signals = (
        _agg("engine-correlation/weighted", 1.0, samples=0),
        _agg("engine-correlation/top1", 1.0, samples=10),
        _agg("complexity-analysis", 0.0, samples=10),
    )
    s = aggregate_score(signals, seed=0)
    assert "engine-correlation/weighted" not in s.dominant_signals


def test_dominant_signals_include_top_contributors() -> None:
    signals = (
        _agg("engine-correlation/weighted", 1.0),
        _agg("regime-shift", 0.5),
        _agg("tactical-detection", 0.2),
    )
    s = aggregate_score(signals, seed=0)
    assert "engine-correlation/weighted" in s.dominant_signals
