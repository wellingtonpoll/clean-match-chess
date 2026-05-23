"""End-to-end `cleanmatch show <run-id>` (T072)."""

from __future__ import annotations

import json
from pathlib import Path

from cleanmatch_cli.main import app
from cleanmatch_cli.output.exit_codes import ExitCode
from typer.testing import CliRunner

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[4]
MORPHY = REPO_ROOT / "tests" / "fixtures" / "pgn" / "known-clean" / "morphy-vs-allies-1858.pgn"


def _run_audit_first(tmp_path: Path, monkeypatch) -> str:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    r = runner.invoke(app, ["audit-game", str(MORPHY), "--output", "json"])
    assert r.exit_code == ExitCode.SUCCESS.value, r.output
    payload = json.loads(r.output.strip().splitlines()[-1])
    return payload["run_id"]


def test_show_unknown_run_user_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    r = runner.invoke(app, ["show", "not-a-real-id"])
    assert r.exit_code == ExitCode.USER_ERROR.value
    assert "not found" in r.output.lower()


def test_show_timeline_after_audit(tmp_path: Path, monkeypatch) -> None:
    run_id = _run_audit_first(tmp_path, monkeypatch)
    r = runner.invoke(app, ["show", run_id])
    assert r.exit_code == ExitCode.SUCCESS.value, r.output
    assert "Risk:" in r.output
    assert run_id[:8] in r.output


def test_show_ply_detail_after_audit(tmp_path: Path, monkeypatch) -> None:
    run_id = _run_audit_first(tmp_path, monkeypatch)
    r = runner.invoke(app, ["show", run_id, "--ply", "0"])
    assert r.exit_code == ExitCode.SUCCESS.value, r.output
    assert "Position complexity" in r.output


def test_show_ply_out_of_range_user_error(tmp_path: Path, monkeypatch) -> None:
    run_id = _run_audit_first(tmp_path, monkeypatch)
    r = runner.invoke(app, ["show", run_id, "--ply", "9999"])
    assert r.exit_code == ExitCode.USER_ERROR.value
