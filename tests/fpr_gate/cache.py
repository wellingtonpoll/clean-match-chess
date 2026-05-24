"""Per-fixture engine-analysis cache for the FPR gate (feature 005 T016).

Each fixture's cached AuditRun is stored at
``tests/fixtures/corpora/.cache/<sha256(pgn_bytes)>.json``. To prevent
stale-cache bugs when a developer swaps the engine or book locally without
busting ``.cache/``, the cache JSON embeds the AuditRun's
``manifest.engine_binary_sha256`` and ``manifest.opening_book_sha256``;
``load_cached`` returns ``None`` (cache miss) on either mismatch.
"""

from __future__ import annotations

import hashlib
import warnings
from pathlib import Path

from shared_types.audit_run import AuditRun

CACHE_DIRNAME = ".cache"


def _pgn_sha256(pgn_path: Path) -> str:
    return hashlib.sha256(pgn_path.read_bytes()).hexdigest()


def cache_path(fixture_pgn: Path, *, corpus_root: Path) -> Path:
    """Return the ``.cache/<sha256>.json`` path for ``fixture_pgn``."""
    sha = _pgn_sha256(fixture_pgn)
    return corpus_root / CACHE_DIRNAME / f"{sha}.json"


def load_cached(
    fixture_pgn: Path,
    *,
    corpus_root: Path,
    expected_engine_sha256: str,
    expected_book_sha256: str,
) -> AuditRun | None:
    """Load the cached AuditRun for ``fixture_pgn``.

    Returns None on cache miss (file absent) OR on engine/book sha256
    mismatch (stale cache after a local artifact swap). On mismatch, emits
    a ``RuntimeWarning`` so the caller knows a forced re-analysis is happening.
    """
    path = cache_path(fixture_pgn, corpus_root=corpus_root)
    if not path.is_file():
        return None
    run = AuditRun.model_validate_json(path.read_text(encoding="utf-8"))
    if run.manifest is None:
        warnings.warn(
            f"cache miss: {path.name} has no manifest (pre-feature-005 entry); forcing re-analysis",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    if run.manifest.engine_binary_sha256 != expected_engine_sha256:
        cached = run.manifest.engine_binary_sha256[:8]
        expected = expected_engine_sha256[:8]
        warnings.warn(
            f"cache miss: {path.name} engine sha256 mismatch "
            f"(cached={cached}..., expected={expected}...)",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    if run.manifest.opening_book_sha256 != expected_book_sha256:
        cached = run.manifest.opening_book_sha256[:8]
        expected = expected_book_sha256[:8]
        warnings.warn(
            f"cache miss: {path.name} book sha256 mismatch "
            f"(cached={cached}..., expected={expected}...)",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    return run


def save_cached(fixture_pgn: Path, run: AuditRun, *, corpus_root: Path) -> Path:
    """Persist ``run`` as the cached audit for ``fixture_pgn``."""
    if run.manifest is None:
        raise ValueError(
            "save_cached: AuditRun.manifest must be populated (feature 005 FR-003) "
            "so the cache can record engine/book sha256 for stale-cache detection"
        )
    path = cache_path(fixture_pgn, corpus_root=corpus_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(run.model_dump_json(), encoding="utf-8")
    return path
