"""End-to-end `cleanmatch export <run-id>` (T082)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from cleanmatch_cli.main import app
from cleanmatch_cli.output.exit_codes import ExitCode
from typer.testing import CliRunner

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[4]
MORPHY = REPO_ROOT / "tests" / "fixtures" / "pgn" / "known-clean" / "morphy-vs-allies-1858.pgn"


def _seed_run(tmp_path: Path, monkeypatch) -> str:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    r = runner.invoke(app, ["audit-game", str(MORPHY), "--output", "json"])
    assert r.exit_code == ExitCode.SUCCESS.value
    payload = json.loads(r.output.strip().splitlines()[-1])
    return payload["run_id"]


def test_export_bundle_creates_zip(tmp_path: Path, monkeypatch) -> None:
    run_id = _seed_run(tmp_path, monkeypatch)
    out = tmp_path / "case.zip"
    r = runner.invoke(app, ["export", run_id, "--out", str(out)])
    assert r.exit_code == ExitCode.SUCCESS.value, r.output
    assert out.is_file()
    with zipfile.ZipFile(out) as zf:
        assert {"report.pdf", "report.html", "report.json", "manifest.json", "README.txt"} == set(
            zf.namelist()
        )


def test_export_json_only(tmp_path: Path, monkeypatch) -> None:
    run_id = _seed_run(tmp_path, monkeypatch)
    out = tmp_path / "report.json"
    r = runner.invoke(app, ["export", run_id, "--format", "json", "--out", str(out)])
    assert r.exit_code == ExitCode.SUCCESS.value, r.output
    assert out.is_file()
    parsed = json.loads(out.read_text())
    assert parsed["run_id"] == run_id


def test_export_unknown_run_user_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    r = runner.invoke(app, ["export", "not-a-real-id", "--out", str(tmp_path / "x.zip")])
    assert r.exit_code == ExitCode.USER_ERROR.value


def test_export_invalid_format(tmp_path: Path, monkeypatch) -> None:
    run_id = _seed_run(tmp_path, monkeypatch)
    out = tmp_path / "report.x"
    r = runner.invoke(app, ["export", run_id, "--format", "xml", "--out", str(out)])
    assert r.exit_code == ExitCode.USER_ERROR.value


def test_export_unsupported_language(tmp_path: Path, monkeypatch) -> None:
    run_id = _seed_run(tmp_path, monkeypatch)
    out = tmp_path / "report.zip"
    r = runner.invoke(app, ["export", run_id, "--language", "fr", "--out", str(out)])
    assert r.exit_code == ExitCode.USER_ERROR.value
