"""End-to-end CLI assertion of v2.0.0 manifest stamping (T048).

Runs `cleanmatch audit-game` on the canonical smoke fixture and reads
the persisted manifest from disk to verify FR-012 / SC-010:

  (a) `scoring_thresholds_version == "2.0.0"`
  (b) `opening_book_sha256` is a non-zero sha256
  (c) `rating_baselines_version` is a non-zero semver
  (d) `signal_versions` contains the bumped per-signal entries

Per-position and per-move shapes are exercised in the analysis-core
integration tests; this test focuses on the manifest contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cleanmatch_cli.main import app
from cleanmatch_cli.output.exit_codes import ExitCode
from typer.testing import CliRunner

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[4]
SMOKE_PGN = REPO_ROOT / "tests" / "fixtures" / "audit_v2_smoke.pgn"


@pytest.mark.skipif(not SMOKE_PGN.is_file(), reason="smoke fixture missing")
def test_audit_v2_manifest_stamps_new_fields(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    r = runner.invoke(app, ["audit-game", str(SMOKE_PGN), "--output", "json"])
    assert r.exit_code == ExitCode.SUCCESS.value, r.output

    payload = json.loads(r.output.strip().splitlines()[-1])
    run_id = payload["run_id"]
    manifest_path = tmp_path / "runs" / run_id / "manifest.json"
    assert manifest_path.is_file(), f"manifest not persisted at {manifest_path}"

    manifest = json.loads(manifest_path.read_text())

    # (a) scoring_thresholds_version bumped
    assert manifest["scoring_thresholds_version"] == "2.0.0", manifest

    # (b) opening_book_sha256 non-zero (bundled book loaded)
    book_sha = manifest["opening_book_sha256"]
    assert isinstance(book_sha, str)
    assert len(book_sha) == 64
    assert book_sha != "0" * 64, "opening book sha256 looks like the unset sentinel"

    # (c) rating_baselines_version is a real semver
    baseline_version = manifest["rating_baselines_version"]
    assert isinstance(baseline_version, str)
    assert baseline_version != "0.0.0", "rating-baselines version is the unset default"

    # (d) signal_versions has the bumped per-signal entries
    sv = manifest["signal_versions"]
    assert isinstance(sv, dict)
    assert sv.get("acpl-analysis") == "1.0.0"
    assert sv.get("regime-shift") == "2.0.0"
    assert sv.get("timing-analysis") == "2.0.0"
    assert sv.get("behavioral-patterns") == "2.0.0"
