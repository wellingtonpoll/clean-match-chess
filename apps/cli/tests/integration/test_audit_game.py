"""End-to-end CLI integration for `cleanmatch audit-game` (T045 + T046)."""

from __future__ import annotations

import json
from pathlib import Path

from cleanmatch_cli.main import app
from cleanmatch_cli.output.exit_codes import ExitCode
from typer.testing import CliRunner

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[4]
MORPHY = REPO_ROOT / "tests" / "fixtures" / "pgn" / "known-clean" / "morphy-vs-allies-1858.pgn"


def test_audit_game_on_morphy_returns_low_risk(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    r = runner.invoke(app, ["audit-game", str(MORPHY), "--output", "json"])
    assert r.exit_code == ExitCode.SUCCESS.value, r.output
    payload = json.loads(r.output.strip().splitlines()[-1])
    assert payload["risk_level"] == "low"
    assert 0.0 <= payload["score"] <= 1.0


def test_audit_game_too_short_returns_user_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    short = tmp_path / "short.pgn"
    short.write_text('[Event "?"]\n[White "a"]\n[Black "b"]\n[Result "*"]\n\n1. e4 e5 *\n')
    r = runner.invoke(app, ["audit-game", str(short)])
    assert r.exit_code == ExitCode.USER_ERROR.value


def test_audit_game_missing_file_returns_user_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    r = runner.invoke(app, ["audit-game", str(tmp_path / "missing.pgn")])
    assert r.exit_code == ExitCode.USER_ERROR.value


def test_audit_game_deterministic_same_arch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    first = runner.invoke(app, ["audit-game", str(MORPHY), "--output", "json"])
    second = runner.invoke(app, ["audit-game", str(MORPHY), "--output", "json"])
    assert first.exit_code == ExitCode.SUCCESS.value
    assert second.exit_code == ExitCode.SUCCESS.value
    # Two runs differ only in their generated run_id; score + risk_level + CI
    # MUST be identical bit-for-bit on the same machine (FR-017 same-arch case).
    a = json.loads(first.output.strip().splitlines()[-1])
    b = json.loads(second.output.strip().splitlines()[-1])
    for key in ("score", "risk_level", "confidence_interval", "dominant_signals"):
        assert a[key] == b[key], f"{key} drifted: {a[key]!r} vs {b[key]!r}"
