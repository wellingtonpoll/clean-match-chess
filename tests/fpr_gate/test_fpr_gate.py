"""Labeled-corpus false-positive-rate gate test target (feature 005 T018).

Single CI-invoked pytest function. Asserts the FPR-gate report against the
thresholds in ``specs/005-scoring-v2-phase2/contracts/fpr_gate.contract.md``.

The test is marked ``@pytest.mark.fpr_gate`` so CI can target it via
``pytest -m fpr_gate``. It is also marked ``slow`` because cold-cache runs
invoke Stockfish per ply (up to 30 min wall on standard runners).

Skipped automatically when the corpus is empty or contains only
``.gitkeep`` (graceful behavior for branches/PRs that have not yet
landed the corpus per FR-005).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.fpr_gate.gate import run_gate
from tests.fpr_gate.provenance import iter_corpus

CORPUS_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "corpora"
REPORT_PATH = CORPUS_ROOT / "fpr_gate_report.json"


def _corpus_has_fixtures() -> bool:
    try:
        return any(True for _ in iter_corpus(CORPUS_ROOT))
    except FileNotFoundError:
        return False


@pytest.mark.fpr_gate
@pytest.mark.slow
def test_fpr_gate_passes() -> None:
    if not _corpus_has_fixtures():
        pytest.skip(
            "feature 005 corpus not yet populated under tests/fixtures/corpora/ "
            "(see specs/005-scoring-v2-phase2/quickstart.md §3 for sourcing)"
        )

    report = run_gate(CORPUS_ROOT)
    REPORT_PATH.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    if not report.passed:
        raise AssertionError(report.format_diagnostic())


@pytest.mark.fpr_gate
def test_fpr_gate_report_artifact_is_well_formed() -> None:
    """If a prior run produced an artifact, verify it parses (smoke sanity)."""
    if not REPORT_PATH.is_file():
        pytest.skip("no fpr_gate_report.json artifact present yet")
    data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert "passed" in data
    assert "fpr" in data
    assert "tpr" in data
    assert "thresholds_version" in data
