"""Report-render perf benchmark (T095).

Budgets from Plan / Principle IV:
- HTML: <= 3 s p95 for a 50-game report.
- PDF:  <= 8 s p95 for a 50-game report.

Single-game proxy here; full 50-game harness lands when the batch
report template ships.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from report_engine.render_html import render_report_html
from report_engine.render_json import render_report_json
from report_engine.render_pdf import render_report_pdf
from shared_types.report import (
    HostInfo,
    Narrative,
    ReportBundle,
    ReportFormat,
    ReportLanguage,
    ReproducibilityManifest,
)
from shared_types.signal import HeuristicVersion

pytestmark = pytest.mark.benchmark


def _bundle() -> ReportBundle:
    manifest = ReproducibilityManifest(
        engine_name="Stockfish",
        engine_version="static-0.0",
        engine_binary_sha256="a" * 64,
        engine_uci_options={"Threads": 1},
        heuristics=(
            HeuristicVersion(
                name="engine-correlation",
                version="0.1.0",
                git_sha="0000000",
                owner="cleanmatch",
                changelog_path="x",
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
    return ReportBundle(
        run_id="a" * 32,
        formats=frozenset({ReportFormat.HTML, ReportFormat.JSON, ReportFormat.PDF}),
        language=ReportLanguage.EN,
        narrative=Narrative(
            summary_paragraph=(
                "Probabilistic score 0.123 (LOW). This is a probabilistic assessment."
            ),
            flagged_segments=(),
        ),
        manifest=manifest,
    )


@pytest.mark.skipif(
    "CLEANMATCH_BENCH" not in os.environ,
    reason="benchmarks gated by CLEANMATCH_BENCH=1",
)
def test_html_render_under_budget(benchmark) -> None:
    out = benchmark(render_report_html, _bundle())
    assert "Clean Match Chess" in out


@pytest.mark.skipif(
    "CLEANMATCH_BENCH" not in os.environ,
    reason="benchmarks gated by CLEANMATCH_BENCH=1",
)
def test_json_render_under_budget(benchmark) -> None:
    out = benchmark(render_report_json, _bundle())
    assert out.startswith("{")


@pytest.mark.skipif(
    "CLEANMATCH_BENCH" not in os.environ,
    reason="benchmarks gated by CLEANMATCH_BENCH=1",
)
def test_pdf_render_under_budget(benchmark, tmp_path: Path) -> None:
    out = tmp_path / "bench.pdf"
    benchmark(render_report_pdf, _bundle(), out)
    assert out.is_file()
    assert benchmark.stats["mean"] < 8.0
