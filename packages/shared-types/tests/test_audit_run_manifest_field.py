"""AuditRun.manifest field — round-trip + extra-forbid invariants (feature 005 T026)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from shared_types.audit_run import (
    AuditRun,
    EngineFingerprint,
    RunMode,
    RunStatus,
)
from shared_types.game import PlayerColor, PlayerRef
from shared_types.report import HostInfo, ReproducibilityManifest
from shared_types.score import RiskLevel, SuspicionScore
from shared_types.signal import HeuristicVersion


def _engine() -> EngineFingerprint:
    return EngineFingerprint(
        name="Stockfish",
        version="16.1",
        binary_sha256="a" * 64,
        uci_options={"Threads": 1, "Hash": 256, "MultiPV": 5},
    )


def _heuristic() -> HeuristicVersion:
    return HeuristicVersion(
        name="engine-correlation",
        version="2.0.0",
        git_sha="abc1234",
        owner="cleanmatch",
        changelog_path="packages/heuristics/CHANGELOG.md",
    )


def _score() -> SuspicionScore:
    return SuspicionScore(score=0.1, risk_level=RiskLevel.LOW, confidence_interval=(0.05, 0.2))


def _subject() -> PlayerRef:
    return PlayerRef(color=PlayerColor.WHITE, username="alice", subject=True)


def _manifest() -> ReproducibilityManifest:
    return ReproducibilityManifest(
        engine_name="Stockfish",
        engine_version="16.1",
        engine_binary_sha256="a" * 64,
        engine_uci_options={"Threads": 1},
        heuristics=(_heuristic(),),
        analysis_core_version="0.1.0",
        report_engine_version="0.1.0",
        python_chess_version="1.999",
        opening_book_sha256="b" * 64,
        input_pgn_sha256="c" * 64,
        started_at=datetime(2026, 5, 24, tzinfo=UTC),
        host=HostInfo(os="Linux", arch="x86_64", cpu_model="test", ram_bytes=8 * 1024**3),
        design_system_version="1.0.0",
        rating_baselines_sha256="d" * 64,
        rating_baselines_version="1.0.0",
        scoring_thresholds_version="2.0.0",
        signal_versions={"acpl-analysis": "1.0.0", "engine-correlation": "2.0.0"},
    )


def _audit_run(*, manifest: ReproducibilityManifest | None = None) -> AuditRun:
    return AuditRun(
        id="abcdef0123",
        created_at=datetime(2026, 5, 24, tzinfo=UTC),
        mode=RunMode.SINGLE_GAME,
        subject=_subject(),
        engine=_engine(),
        heuristic_set=(_heuristic(),),
        score=_score(),
        status=RunStatus.COMPLETE,
        manifest=manifest,
    )


def test_manifest_defaults_to_none() -> None:
    run = AuditRun(
        id="abcdef0123",
        created_at=datetime(2026, 5, 24, tzinfo=UTC),
        mode=RunMode.SINGLE_GAME,
        subject=_subject(),
        engine=_engine(),
        heuristic_set=(_heuristic(),),
        score=_score(),
    )
    assert run.manifest is None


def test_manifest_attached_round_trips_byte_identical() -> None:
    run = _audit_run(manifest=_manifest())
    serialized = run.model_dump_json()
    restored = AuditRun.model_validate_json(serialized)
    assert restored.manifest is not None
    assert restored.manifest.rating_baselines_sha256 == "d" * 64
    assert restored.manifest.signal_versions == {
        "acpl-analysis": "1.0.0",
        "engine-correlation": "2.0.0",
    }
    assert restored.model_dump_json() == serialized


def test_extra_forbid_still_rejects_unknown_keys() -> None:
    serialized = _audit_run(manifest=_manifest()).model_dump_json()
    bad = serialized[:-1] + ',"unknown_key":42}'
    with pytest.raises(ValidationError):
        AuditRun.model_validate_json(bad)
