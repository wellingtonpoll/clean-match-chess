"""Reproducibility manifest builder.

Builds a `ReproducibilityManifest` from engine fingerprint, heuristic
registry snapshot, library versions, input PGN SHA256, opening-book
SHA256, host info, and the design-system version. The manifest's
SHA256 (computed by `manifest_hash`) is the deterministic cache key
used by `pipeline.cache`.
"""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import UTC, datetime
from importlib import metadata
from typing import Final

from shared_types.audit_run import EngineFingerprint
from shared_types.report import HostInfo, ReproducibilityManifest
from shared_types.signal import HeuristicVersion

ANALYSIS_CORE_VERSION: Final[str] = "0.1.0"

_HASH_FIELDS: Final[tuple[str, ...]] = (
    "engine_name",
    "engine_version",
    "engine_binary_sha256",
    "engine_uci_options",
    "heuristics",
    "analysis_core_version",
    "report_engine_version",
    "python_chess_version",
    "opening_book_sha256",
    "input_pgn_sha256",
    "design_system_version",
)


def build_manifest(
    *,
    engine: EngineFingerprint,
    heuristics: tuple[HeuristicVersion, ...],
    input_pgn_sha256: str,
    opening_book_sha256: str,
    design_system_version: str,
    report_engine_version: str | None = None,
    started_at: datetime | None = None,
) -> ReproducibilityManifest:
    return ReproducibilityManifest(
        engine_name=engine.name,
        engine_version=engine.version,
        engine_binary_sha256=engine.binary_sha256,
        engine_uci_options=engine.uci_options,
        heuristics=heuristics,
        analysis_core_version=ANALYSIS_CORE_VERSION,
        report_engine_version=report_engine_version or _package_version("report-engine"),
        python_chess_version=_package_version("python-chess"),
        opening_book_sha256=opening_book_sha256,
        input_pgn_sha256=input_pgn_sha256,
        started_at=started_at or datetime.now(UTC),
        host=_collect_host_info(),
        design_system_version=design_system_version,
    )


def manifest_hash(manifest: ReproducibilityManifest) -> str:
    """Deterministic SHA256 over the cache-relevant fields of a manifest.

    `started_at` and `host` are EXCLUDED so the same logical run produces
    the same cache key across machines and clock skew.
    """
    payload = manifest.model_dump(mode="json", include=set(_HASH_FIELDS))
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "0.0.0"


def _collect_host_info() -> HostInfo:
    return HostInfo(
        os=platform.system(),
        arch=platform.machine(),
        cpu_model=platform.processor() or "unknown",
        ram_bytes=0,
    )
