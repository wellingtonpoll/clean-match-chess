"""End-to-end gate orchestration smoke test against the synthetic mini-corpus.

The mini-corpus at ``tests/fixtures/corpora/_smoke/`` is not picked up by
the real FPR gate (``iter_corpus`` only walks ``clean/`` and
``engine_assisted/`` directly under the corpus root). Tests here invoke
``run_gate`` against the mini-corpus directly and assert orchestration
behavior with a stubbed audit callback. Feature 005 T015.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from shared_types.audit_run import AuditRun, EngineFingerprint, RunMode, RunStatus
from shared_types.game import PlayerColor, PlayerRef
from shared_types.report import HostInfo, ReproducibilityManifest
from shared_types.score import SuspicionScore, risk_level_for
from shared_types.signal import HeuristicVersion

from tests.fpr_gate.gate import run_gate

SMOKE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "corpora" / "_smoke"


def _heuristic() -> HeuristicVersion:
    return HeuristicVersion(
        name="acpl-analysis",
        version="1.0.0",
        git_sha="0000000",
        owner="cleanmatch",
        changelog_path="packages/heuristics/CHANGELOG.md",
    )


def _stub_audit(score: float) -> AuditRun:
    return AuditRun(
        id="0" * 32,
        created_at=datetime(2026, 5, 24, tzinfo=UTC),
        mode=RunMode.SINGLE_GAME,
        subject=PlayerRef(color=PlayerColor.WHITE, username="W", subject=True),
        engine=EngineFingerprint(name="Stockfish", version="t", binary_sha256="a" * 64),
        heuristic_set=(_heuristic(),),
        score=SuspicionScore(
            score=score,
            risk_level=risk_level_for(score),
            confidence_interval=(max(0.0, score - 0.1), min(1.0, score + 0.1)),
        ),
        status=RunStatus.COMPLETE,
        manifest=ReproducibilityManifest(
            engine_name="Stockfish",
            engine_version="t",
            engine_binary_sha256="a" * 64,
            engine_uci_options={},
            heuristics=(_heuristic(),),
            analysis_core_version="0.1.0",
            report_engine_version="0.1.0",
            python_chess_version="1.999",
            opening_book_sha256="b" * 64,
            input_pgn_sha256="c" * 64,
            started_at=datetime(2026, 5, 24, tzinfo=UTC),
            host=HostInfo(os="Linux", arch="x86_64", cpu_model="t", ram_bytes=8 * 1024**3),
            design_system_version="1.0.0",
            rating_baselines_sha256="d" * 64,
            rating_baselines_version="1.0.0",
            scoring_thresholds_version="2.0.0",
            signal_versions={"acpl-analysis": "1.0.0"},
        ),
    )


def _is_clean_fixture(path: Path) -> bool:
    """Match the immediate parent dir to avoid spurious 'clean' matches
    in the repo path (clean-match-chess)."""
    return path.parent.name == "clean"


def test_gate_passes_on_smoke_corpus_with_perfect_classifier() -> None:
    def stub(path: Path) -> AuditRun:
        return _stub_audit(0.10 if _is_clean_fixture(path) else 0.85)

    report = run_gate(SMOKE_ROOT, audit_callback=stub, use_cache=False)
    # The smoke corpus has 1 clean + 1 engine_assisted; perfect classifier
    # → 0% FPR and 100% TPR. (1 engine_assisted hit meets the 80% TPR
    # threshold by direct equality at 1.0 ≥ 0.8.)
    assert report.passed is True
    assert report.fpr == 0.0
    assert report.tpr == 1.0


def test_gate_fails_when_classifier_inverted() -> None:
    def stub(path: Path) -> AuditRun:
        return _stub_audit(0.85 if _is_clean_fixture(path) else 0.10)

    report = run_gate(SMOKE_ROOT, audit_callback=stub, use_cache=False)
    assert report.passed is False
    assert report.fpr == 1.0
    assert report.tpr == 0.0
