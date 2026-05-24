"""Unit tests for the provenance sidecar loader (feature 005 T006)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.fpr_gate.provenance import (
    ProvenanceRecord,
    iter_corpus,
    load_provenance,
    sidecar_path,
)

SMOKE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "corpora" / "_smoke"


def test_load_clean_smoke_fixture() -> None:
    pgn = SMOKE_ROOT / "clean" / "smoke_clean_001.pgn"
    rec = load_provenance(pgn)
    assert isinstance(rec, ProvenanceRecord)
    assert rec.label == "clean"
    assert rec.label_confidence == "high"
    assert rec.source == "synthetic-smoke-fixture-feature-005"


def test_load_engine_assisted_smoke_fixture() -> None:
    pgn = SMOKE_ROOT / "engine_assisted" / "smoke_ea_001.pgn"
    rec = load_provenance(pgn)
    assert rec.label == "engine_assisted"


def test_missing_sidecar_raises(tmp_path: Path) -> None:
    pgn = tmp_path / "orphan.pgn"
    pgn.write_text("[Event ?]\n\n*\n")
    with pytest.raises(FileNotFoundError, match="provenance sidecar missing"):
        load_provenance(pgn)


def test_invalid_label_raises(tmp_path: Path) -> None:
    pgn = tmp_path / "bad.pgn"
    pgn.write_text("[Event ?]\n\n*\n")
    sidecar_path(pgn).write_text(
        json.dumps(
            {
                "source": "x",
                "retrieved_at": "2026-05-24T00:00:00Z",
                "label": "neither",
                "label_confidence": "high",
                "notes": "",
            }
        )
    )
    with pytest.raises(ValidationError):
        load_provenance(pgn)


def test_iter_corpus_discovers_both_subdirs() -> None:
    pairs = list(iter_corpus(SMOKE_ROOT))
    labels = sorted(rec.label for _, rec in pairs)
    assert labels == ["clean", "engine_assisted"]


def test_iter_corpus_skips_non_pgn(tmp_path: Path) -> None:
    (tmp_path / "clean").mkdir()
    (tmp_path / "clean" / "notes.txt").write_text("ignored")
    pairs = list(iter_corpus(tmp_path))
    assert pairs == []


def test_iter_corpus_handles_missing_subdir(tmp_path: Path) -> None:
    pairs = list(iter_corpus(tmp_path))
    assert pairs == []


def test_iter_corpus_orphan_pgn_raises(tmp_path: Path) -> None:
    (tmp_path / "clean").mkdir()
    (tmp_path / "clean" / "orphan.pgn").write_text("[Event ?]\n\n*\n")
    with pytest.raises(FileNotFoundError):
        list(iter_corpus(tmp_path))
