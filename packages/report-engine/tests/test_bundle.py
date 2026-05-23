"""Bundle writer + lexical-audit gate (T090, T092)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from report_engine.bundle import write_bundle
from report_engine.lexical_audit import LexicalAuditError


def test_bundle_creates_zip_with_expected_files(bundle, tmp_path: Path) -> None:
    out = tmp_path / "case.zip"
    artefacts = write_bundle(bundle, out)
    assert artefacts.archive_path == out
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
    assert names == {
        "report.pdf",
        "report.html",
        "report.json",
        "manifest.json",
        "README.txt",
    }


def test_bundle_lexical_audit_blocks_forbidden_render(bundle, tmp_path: Path) -> None:
    # Inject a forbidden term into the narrative; the bundle MUST refuse.
    poisoned = bundle.model_copy(
        update={
            "narrative": bundle.narrative.model_copy(
                update={"summary_paragraph": "this player is a cheater"}
            )
        }
    )
    out = tmp_path / "poisoned.zip"
    with pytest.raises(LexicalAuditError):
        write_bundle(poisoned, out)
    assert not out.exists()


def test_bundle_html_uses_metric_role(bundle, tmp_path: Path) -> None:
    out = tmp_path / "case.zip"
    write_bundle(bundle, out)
    with zipfile.ZipFile(out) as zf:
        html = zf.read("report.html").decode("utf-8")
    assert 'data-role="metric-card-headline"' in html
