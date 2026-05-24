"""Unit tests for the FPR-gate internals (feature 005 T014)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from shared_types.audit_run import AuditRun, EngineFingerprint, RunMode, RunStatus
from shared_types.game import PlayerColor, PlayerRef
from shared_types.report import HostInfo, ReproducibilityManifest
from shared_types.score import SuspicionScore, risk_level_for
from shared_types.signal import HeuristicVersion

from tests.fpr_gate.cache import cache_path, load_cached, save_cached
from tests.fpr_gate.gate import (
    DEFAULT_FPR_THRESHOLD,
    DEFAULT_TPR_THRESHOLD,
    FixtureOutcome,
    FprGateReport,
    run_gate,
    wilson_score_interval,
)
from tests.fpr_gate.provenance import sidecar_path


def _engine_sha() -> str:
    return "a" * 64


def _book_sha() -> str:
    return "b" * 64


def _heuristic() -> HeuristicVersion:
    return HeuristicVersion(
        name="acpl-analysis",
        version="1.0.0",
        git_sha="0000000",
        owner="cleanmatch",
        changelog_path="packages/heuristics/CHANGELOG.md",
    )


def _manifest(*, engine: str | None = None, book: str | None = None) -> ReproducibilityManifest:
    return ReproducibilityManifest(
        engine_name="Stockfish",
        engine_version="test",
        engine_binary_sha256=engine or _engine_sha(),
        engine_uci_options={},
        heuristics=(_heuristic(),),
        analysis_core_version="0.1.0",
        report_engine_version="0.1.0",
        python_chess_version="1.999",
        opening_book_sha256=book or _book_sha(),
        input_pgn_sha256="c" * 64,
        started_at=datetime(2026, 5, 24, tzinfo=UTC),
        host=HostInfo(os="Linux", arch="x86_64", cpu_model="t", ram_bytes=8 * 1024**3),
        design_system_version="1.0.0",
        rating_baselines_sha256="d" * 64,
        rating_baselines_version="1.0.0",
        scoring_thresholds_version="2.0.0",
        signal_versions={"acpl-analysis": "1.0.0"},
    )


def _audit(score_value: float, *, engine: str | None = None, book: str | None = None) -> AuditRun:
    return AuditRun(
        id="0" * 32,
        created_at=datetime(2026, 5, 24, tzinfo=UTC),
        mode=RunMode.SINGLE_GAME,
        subject=PlayerRef(color=PlayerColor.WHITE, username="W", subject=True),
        engine=EngineFingerprint(
            name="Stockfish",
            version="test",
            binary_sha256=engine or _engine_sha(),
        ),
        heuristic_set=(_heuristic(),),
        score=SuspicionScore(
            score=score_value,
            risk_level=risk_level_for(score_value),
            confidence_interval=(max(0.0, score_value - 0.1), min(1.0, score_value + 0.1)),
        ),
        status=RunStatus.COMPLETE,
        manifest=_manifest(engine=engine, book=book),
    )


# ---------- Wilson CI ----------


def test_wilson_zero_trials_returns_full_range() -> None:
    assert wilson_score_interval(0, 0) == (0.0, 1.0)


def test_wilson_proportion_zero() -> None:
    lo, hi = wilson_score_interval(0, 50)
    assert lo == 0.0
    assert 0.04 < hi < 0.08


def test_wilson_proportion_half() -> None:
    lo, hi = wilson_score_interval(10, 20)
    assert lo < 0.5 < hi
    assert abs((lo + hi) / 2 - 0.5) < 0.05


def test_wilson_proportion_full() -> None:
    lo, hi = wilson_score_interval(20, 20)
    assert hi == 1.0
    assert lo > 0.8


# ---------- Cache hit/miss ----------


def test_cache_save_then_load_byte_identical(tmp_path: Path) -> None:
    pgn = tmp_path / "clean" / "fixture.pgn"
    pgn.parent.mkdir(parents=True)
    pgn.write_bytes(b"[Event ?]\n\n*\n")
    run = _audit(0.42)
    save_cached(pgn, run, corpus_root=tmp_path)
    loaded = load_cached(
        pgn,
        corpus_root=tmp_path,
        expected_engine_sha256=_engine_sha(),
        expected_book_sha256=_book_sha(),
    )
    assert loaded is not None
    assert loaded.id == run.id
    assert loaded.score is not None and loaded.score.score == 0.42


def test_cache_miss_on_engine_sha_mismatch(tmp_path: Path) -> None:
    pgn = tmp_path / "clean" / "fixture.pgn"
    pgn.parent.mkdir(parents=True)
    pgn.write_bytes(b"[Event ?]\n\n*\n")
    save_cached(pgn, _audit(0.42), corpus_root=tmp_path)
    with pytest.warns(RuntimeWarning, match="engine sha256 mismatch"):
        loaded = load_cached(
            pgn,
            corpus_root=tmp_path,
            expected_engine_sha256="f" * 64,
            expected_book_sha256=_book_sha(),
        )
    assert loaded is None


def test_cache_miss_on_book_sha_mismatch(tmp_path: Path) -> None:
    pgn = tmp_path / "clean" / "fixture.pgn"
    pgn.parent.mkdir(parents=True)
    pgn.write_bytes(b"[Event ?]\n\n*\n")
    save_cached(pgn, _audit(0.42), corpus_root=tmp_path)
    with pytest.warns(RuntimeWarning, match="book sha256 mismatch"):
        loaded = load_cached(
            pgn,
            corpus_root=tmp_path,
            expected_engine_sha256=_engine_sha(),
            expected_book_sha256="f" * 64,
        )
    assert loaded is None


def test_cache_miss_on_absent_file(tmp_path: Path) -> None:
    pgn = tmp_path / "clean" / "fixture.pgn"
    pgn.parent.mkdir(parents=True)
    pgn.write_bytes(b"[Event ?]\n\n*\n")
    loaded = load_cached(
        pgn,
        corpus_root=tmp_path,
        expected_engine_sha256=_engine_sha(),
        expected_book_sha256=_book_sha(),
    )
    assert loaded is None


def test_save_cached_rejects_run_without_manifest(tmp_path: Path) -> None:
    pgn = tmp_path / "clean" / "fixture.pgn"
    pgn.parent.mkdir(parents=True)
    pgn.write_bytes(b"[Event ?]\n\n*\n")
    run = _audit(0.42)
    run = run.model_copy(update={"manifest": None})
    with pytest.raises(ValueError, match="manifest must be populated"):
        save_cached(pgn, run, corpus_root=tmp_path)


def test_cache_path_keyed_by_pgn_sha256(tmp_path: Path) -> None:
    p1 = tmp_path / "a.pgn"
    p2 = tmp_path / "b.pgn"
    p1.write_bytes(b"content-1")
    p2.write_bytes(b"content-2")
    assert cache_path(p1, corpus_root=tmp_path) != cache_path(p2, corpus_root=tmp_path)
    # Same content → same path.
    p3 = tmp_path / "c.pgn"
    p3.write_bytes(b"content-1")
    assert cache_path(p1, corpus_root=tmp_path) == cache_path(p3, corpus_root=tmp_path)


# ---------- run_gate orchestration with stubbed audit ----------


def _make_fixture(
    tmp_path: Path,
    name: str,
    label: str,
    *,
    subdir: str | None = None,
) -> Path:
    subdir = subdir or ("clean" if label == "clean" else "engine_assisted")
    pgn = tmp_path / subdir / f"{name}.pgn"
    pgn.parent.mkdir(parents=True, exist_ok=True)
    pgn.write_text("[Event ?]\n\n*\n")
    sidecar_path(pgn).write_text(
        '{"source":"s","retrieved_at":"2026-05-24T00:00:00Z",'
        f'"label":"{label}","label_confidence":"high","notes":""}}'
    )
    return pgn


def test_run_gate_passes_when_thresholds_satisfied(tmp_path: Path) -> None:
    for i in range(5):
        _make_fixture(tmp_path, f"c{i}", "clean")
    for i in range(5):
        _make_fixture(tmp_path, f"e{i}", "engine_assisted")

    def stub(path: Path) -> AuditRun:
        # Clean → low scores; engine_assisted → high scores.
        if "clean" in str(path):
            return _audit(0.10)
        return _audit(0.85)

    report = run_gate(tmp_path, audit_callback=stub, use_cache=False)
    assert report.passed is True
    assert report.fpr == 0.0
    assert report.tpr == 1.0
    assert report.clean_corpus_size == 5
    assert report.engine_assisted_corpus_size == 5


def test_run_gate_fails_on_high_fpr(tmp_path: Path) -> None:
    for i in range(10):
        _make_fixture(tmp_path, f"c{i}", "clean")
    for i in range(5):
        _make_fixture(tmp_path, f"e{i}", "engine_assisted")

    def stub(path: Path) -> AuditRun:
        # 3/10 clean games incorrectly scored high → FPR 30%
        if "clean" in str(path):
            idx = int(path.stem.lstrip("c"))
            return _audit(0.85 if idx < 3 else 0.10)
        return _audit(0.85)

    report = run_gate(tmp_path, audit_callback=stub, use_cache=False)
    assert report.passed is False
    assert report.fpr == 0.3
    assert len(report.false_positives) == 3


def test_run_gate_fails_on_low_tpr(tmp_path: Path) -> None:
    for i in range(5):
        _make_fixture(tmp_path, f"c{i}", "clean")
    for i in range(10):
        _make_fixture(tmp_path, f"e{i}", "engine_assisted")

    def stub(path: Path) -> AuditRun:
        if "clean" in str(path):
            return _audit(0.10)
        # 5/10 engine_assisted missed → TPR 50% < 80%
        idx = int(path.stem.lstrip("e"))
        return _audit(0.85 if idx < 5 else 0.20)

    report = run_gate(tmp_path, audit_callback=stub, use_cache=False)
    assert report.passed is False
    assert report.tpr == 0.5
    assert len(report.false_negatives) == 5


def test_diagnostic_format_includes_offenders(tmp_path: Path) -> None:
    _make_fixture(tmp_path, "c0", "clean")
    _make_fixture(tmp_path, "e0", "engine_assisted")

    def stub(path: Path) -> AuditRun:
        return _audit(0.85 if "clean" in str(path) else 0.30)

    report = run_gate(tmp_path, audit_callback=stub, use_cache=False)
    diag = report.format_diagnostic()
    assert "FPR gate FAILED" in diag
    assert "c0.pgn" in diag
    assert "e0.pgn" in diag


def test_run_gate_empty_corpus_returns_zero_sized_report(tmp_path: Path) -> None:
    def stub(path: Path) -> AuditRun:
        return _audit(0.0)

    report = run_gate(tmp_path, audit_callback=stub, use_cache=False)
    assert report.clean_corpus_size == 0
    assert report.engine_assisted_corpus_size == 0
    assert report.fpr == 0.0
    assert report.tpr == 0.0
    # No clean fixtures means FPR threshold trivially holds; no engine_assisted
    # means TPR can't satisfy ≥ 0.8 (0 ≥ 0.8 is false), so gate fails. That's
    # the safe default for an empty corpus.
    assert report.passed is False


def test_report_round_trips_via_json(tmp_path: Path) -> None:
    _make_fixture(tmp_path, "c0", "clean")
    _make_fixture(tmp_path, "e0", "engine_assisted")

    def stub(path: Path) -> AuditRun:
        return _audit(0.10 if "clean" in str(path) else 0.85)

    report = run_gate(tmp_path, audit_callback=stub, use_cache=False)
    serialized = report.model_dump_json()
    restored = FprGateReport.model_validate_json(serialized)
    assert restored == report


def test_default_thresholds_match_contract() -> None:
    assert DEFAULT_FPR_THRESHOLD == 0.020
    assert DEFAULT_TPR_THRESHOLD == 0.800


def test_classification_outcomes_use_target_label(tmp_path: Path) -> None:
    """Regression guard for FixtureOutcome.classification field."""
    _make_fixture(tmp_path, "c0", "clean")

    def stub(path: Path) -> AuditRun:
        return _audit(0.99)

    report = run_gate(tmp_path, audit_callback=stub, use_cache=False)
    assert len(report.false_positives) == 1
    assert isinstance(report.false_positives[0], FixtureOutcome)
    assert report.false_positives[0].classification == "false_positive"
