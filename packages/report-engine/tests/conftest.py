"""Shared fixtures for report-engine tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from shared_types.report import (
    HostInfo,
    Narrative,
    ReportBundle,
    ReportFormat,
    ReportLanguage,
    ReproducibilityManifest,
)
from shared_types.signal import HeuristicVersion


@pytest.fixture
def manifest() -> ReproducibilityManifest:
    return ReproducibilityManifest(
        engine_name="Stockfish",
        engine_version="static-0.0",
        engine_binary_sha256="a" * 64,
        engine_uci_options={"Threads": 1, "MultiPV": 5},
        heuristics=(
            HeuristicVersion(
                name="engine-correlation",
                version="0.1.0",
                git_sha="0000000",
                owner="cleanmatch",
                changelog_path="packages/heuristics/CHANGELOG.md",
            ),
        ),
        analysis_core_version="0.1.0",
        report_engine_version="0.1.0",
        python_chess_version="1.999",
        opening_book_sha256="b" * 64,
        input_pgn_sha256="c" * 64,
        started_at=datetime(2026, 5, 23, 12, 0, tzinfo=UTC),
        host=HostInfo(os="Linux", arch="x86_64", cpu_model="test", ram_bytes=0),
        design_system_version="0.1.0",
    )


@pytest.fixture
def bundle(manifest: ReproducibilityManifest) -> ReportBundle:
    return ReportBundle(
        run_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        formats=frozenset({ReportFormat.HTML, ReportFormat.JSON, ReportFormat.PDF}),
        language=ReportLanguage.EN,
        narrative=Narrative(
            summary_paragraph=(
                "Probabilistic score 0.123 (LOW). 95% CI (0.05, 0.20). "
                "Dominant signal: complexity-analysis. This is a probabilistic "
                "assessment, not an accusation."
            ),
            flagged_segments=(),
        ),
        manifest=manifest,
    )


@pytest.fixture
def cleanmatch_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    return tmp_path
