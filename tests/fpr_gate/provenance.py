"""Provenance sidecar loader and validator (feature 005 FR-005).

Every PGN fixture under ``tests/fixtures/corpora/clean/`` or
``tests/fixtures/corpora/engine_assisted/`` MUST have a sibling
``<stem>.provenance.json`` matching ``ProvenanceRecord``.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProvenanceLabel = Literal["clean", "engine_assisted"]
ProvenanceConfidence = Literal["high", "medium", "low"]


class ProvenanceRecord(BaseModel):
    """Sibling provenance metadata for a corpus PGN fixture."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = Field(min_length=1)
    retrieved_at: str = Field(
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})$"
    )
    label: ProvenanceLabel
    label_confidence: ProvenanceConfidence
    notes: str


def sidecar_path(pgn_path: Path) -> Path:
    """Return the expected ``.provenance.json`` path for a PGN file."""

    return pgn_path.with_suffix(".provenance.json")


def load_provenance(pgn_path: Path) -> ProvenanceRecord:
    """Load and validate the provenance sidecar for ``pgn_path``.

    Raises ``FileNotFoundError`` if the sidecar is missing, and pydantic
    ``ValidationError`` if the JSON does not match ``ProvenanceRecord``.
    """

    sidecar = sidecar_path(pgn_path)
    if not sidecar.is_file():
        raise FileNotFoundError(
            f"provenance sidecar missing: {sidecar} (every corpus PGN MUST have one)"
        )
    return ProvenanceRecord.model_validate_json(sidecar.read_text(encoding="utf-8"))


def iter_corpus(corpus_root: Path) -> Iterator[tuple[Path, ProvenanceRecord]]:
    """Yield ``(pgn_path, provenance)`` for every PGN under ``clean/`` and ``engine_assisted/``.

    Skips ``.cache/``, ``_smoke/``, hidden files, and any non-PGN sibling. Sorts by
    path for determinism. Raises on any PGN lacking a valid sidecar.
    """

    for subdir_name in ("clean", "engine_assisted"):
        subdir = corpus_root / subdir_name
        if not subdir.is_dir():
            continue
        for pgn_path in sorted(subdir.glob("*.pgn")):
            if pgn_path.name.startswith("."):
                continue
            yield pgn_path, load_provenance(pgn_path)
