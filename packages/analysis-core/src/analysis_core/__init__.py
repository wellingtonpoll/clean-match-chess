"""Ingest, engine, and pipeline orchestration."""

from __future__ import annotations

from analysis_core.manifest import build_manifest, manifest_hash
from analysis_core.pipeline.run import (
    DEFAULT_DESIGN_SYSTEM_VERSION,
    DEFAULT_OPENING_BOOK_SHA256,
    run_single_game,
    run_username_batch,
)

__all__: list[str] = [
    "DEFAULT_DESIGN_SYSTEM_VERSION",
    "DEFAULT_OPENING_BOOK_SHA256",
    "build_manifest",
    "manifest_hash",
    "run_single_game",
    "run_username_batch",
]
