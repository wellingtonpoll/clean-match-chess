"""Shared fixtures for analysis-core tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from analysis_core.manifest import build_manifest
from shared_types.audit_run import EngineFingerprint
from shared_types.signal import HeuristicVersion


@pytest.fixture
def engine_fp() -> EngineFingerprint:
    return EngineFingerprint(
        name="Stockfish",
        version="16.1",
        binary_sha256="a" * 64,
        uci_options={"Threads": 1, "Hash": 256, "MultiPV": 5, "UseNNUE": True},
    )


@pytest.fixture
def heuristics() -> tuple[HeuristicVersion, ...]:
    return (
        HeuristicVersion(
            name="engine-correlation",
            version="0.1.0",
            git_sha="abc1234",
            owner="cleanmatch",
            changelog_path="packages/heuristics/CHANGELOG.md",
        ),
    )


@pytest.fixture
def manifest_factory(engine_fp, heuristics):
    def _make(
        *,
        input_pgn_sha256: str = "1" * 64,
        opening_book_sha256: str = "2" * 64,
        design_system_version: str = "1.0.0",
        started_at: datetime | None = None,
    ):
        return build_manifest(
            engine=engine_fp,
            heuristics=heuristics,
            input_pgn_sha256=input_pgn_sha256,
            opening_book_sha256=opening_book_sha256,
            design_system_version=design_system_version,
            started_at=started_at or datetime(2026, 5, 23, 12, 0, tzinfo=UTC),
        )

    return _make


@pytest.fixture
def cleanmatch_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    return tmp_path
