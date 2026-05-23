"""End-to-end `cleanmatch audit-username` integration (T064)."""

from __future__ import annotations

import json
from pathlib import Path

from cleanmatch_cli.main import app
from cleanmatch_cli.output.exit_codes import ExitCode
from typer.testing import CliRunner

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[4]
MORPHY = REPO_ROOT / "tests" / "fixtures" / "pgn" / "known-clean" / "morphy-vs-allies-1858.pgn"


def _archives_url() -> str:
    return "https://api.chess.com/pub/player/alice/games/archives"


def _archive_url(year: int, month: int) -> str:
    return f"https://api.chess.com/pub/player/alice/games/{year}/{month:02d}"


def test_audit_username_two_games_happy_path(httpx_mock, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    pgn_text = MORPHY.read_text()
    httpx_mock.add_response(
        method="GET",
        url=_archives_url(),
        json={"archives": [_archive_url(2026, 5)]},
    )
    httpx_mock.add_response(
        method="GET",
        url=_archive_url(2026, 5),
        json={
            "games": [
                {"pgn": pgn_text, "time_class": "rapid", "end_time": 200},
                {"pgn": pgn_text, "time_class": "rapid", "end_time": 100},
            ]
        },
    )

    r = runner.invoke(app, ["audit-username", "alice", "--count", "2", "--output", "json"])
    assert r.exit_code == ExitCode.SUCCESS.value, r.output
    payload = json.loads(r.output.strip().splitlines()[-1])
    assert payload["username"] == "alice"
    assert payload["games_audited"] == 2
    assert payload["risk_level"] == "low"


def test_audit_username_unsupported_platform_user_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    r = runner.invoke(app, ["audit-username", "alice", "--platform", "lichess", "--count", "1"])
    assert r.exit_code == ExitCode.USER_ERROR.value


def test_audit_username_invalid_time_control_user_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    r = runner.invoke(
        app,
        [
            "audit-username",
            "alice",
            "--count",
            "1",
            "--time-control",
            "ultra,blitz",
        ],
    )
    assert r.exit_code == ExitCode.USER_ERROR.value


def test_audit_username_no_eligible_games(httpx_mock, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    httpx_mock.add_response(
        method="GET",
        url=_archives_url(),
        json={"archives": [_archive_url(2026, 5)]},
    )
    httpx_mock.add_response(
        method="GET",
        url=_archive_url(2026, 5),
        json={
            "games": [
                {
                    "pgn": '[Event "?"]\n[White "a"]\n[Black "b"]\n[Result "*"]\n\n1. e4 e5 *\n',
                    "time_class": "rapid",
                    "end_time": 200,
                }
            ]
        },
    )
    r = runner.invoke(app, ["audit-username", "alice", "--count", "1"])
    assert r.exit_code == ExitCode.USER_ERROR.value


def test_audit_username_upstream_failure(httpx_mock, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))
    httpx_mock.add_response(method="GET", url=_archives_url(), status_code=500)
    httpx_mock.add_response(method="GET", url=_archives_url(), status_code=500)
    httpx_mock.add_response(method="GET", url=_archives_url(), status_code=500)
    httpx_mock.add_response(method="GET", url=_archives_url(), status_code=500)
    r = runner.invoke(app, ["audit-username", "alice", "--count", "1"])
    assert r.exit_code == ExitCode.UPSTREAM_ERROR.value
