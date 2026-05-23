"""Filesystem-backed cache keyed by reproducibility-manifest hash.

Layout under `${CLEANMATCH_HOME:-~/.cleanmatch}/runs/<manifest-hash>/`:
- `manifest.json`
- subsequent payloads written by the pipeline runner

This module only owns the keyspace + lookup + write; it does NOT
know what payload shapes go inside.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Final

from shared_types.report import ReproducibilityManifest

from analysis_core.manifest import manifest_hash

_HOME_ENV: Final[str] = "CLEANMATCH_HOME"
_DEFAULT_HOME: Final[Path] = Path.home() / ".cleanmatch"


def cleanmatch_home() -> Path:
    raw = os.environ.get(_HOME_ENV)
    return Path(raw).expanduser() if raw else _DEFAULT_HOME


def runs_dir() -> Path:
    return cleanmatch_home() / "runs"


def run_dir_for(manifest: ReproducibilityManifest) -> Path:
    return runs_dir() / manifest_hash(manifest)


def is_cached(manifest: ReproducibilityManifest) -> bool:
    return (run_dir_for(manifest) / "manifest.json").is_file()


def persist_manifest(manifest: ReproducibilityManifest) -> Path:
    dest = run_dir_for(manifest)
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / "manifest.json"
    payload = manifest.model_dump(mode="json")
    target.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str))
    return target


def load_manifest(manifest_dir: Path) -> ReproducibilityManifest:
    raw = (manifest_dir / "manifest.json").read_text()
    return ReproducibilityManifest.model_validate_json(raw)
