"""CLI flag grammar + exit-code contract surface tests.

These tests use Typer's CliRunner to exercise the surface only. They
assert: every subcommand is wired, the documented flags are accepted,
exit codes follow the constitution Principle III mapping.
"""

from __future__ import annotations

import pytest
from cleanmatch_cli.main import app
from cleanmatch_cli.output.exit_codes import ExitCode, for_error_code
from typer.testing import CliRunner

runner = CliRunner()


def test_top_level_help_lists_all_subcommands() -> None:
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == ExitCode.SUCCESS.value
    for cmd in ("audit-game", "audit-username", "show", "export"):
        assert cmd in r.stdout


@pytest.mark.parametrize(
    "argv",
    [
        ["audit-game", "--help"],
        ["audit-username", "--help"],
        ["show", "--help"],
        ["export", "--help"],
    ],
)
def test_subcommand_help_succeeds(argv: list[str]) -> None:
    r = runner.invoke(app, argv)
    assert r.exit_code == ExitCode.SUCCESS.value


def test_for_error_code_mapping() -> None:
    assert for_error_code("user_error") is ExitCode.USER_ERROR
    assert for_error_code("upstream_error") is ExitCode.UPSTREAM_ERROR
    assert for_error_code("internal_error") is ExitCode.INTERNAL_ERROR


def test_for_error_code_unknown_raises() -> None:
    with pytest.raises(KeyError):
        for_error_code("does-not-exist")


def test_audit_game_accepts_documented_flags() -> None:
    r = runner.invoke(
        app,
        [
            "--log-format",
            "json",
            "--log-level",
            "debug",
            "audit-game",
            "/tmp/missing.pgn",
            "--subject",
            "white",
            "--depth",
            "18",
            "--multipv",
            "5",
            "--output",
            "json",
            "--language",
            "en",
            "--no-cache",
            "--debug",
        ],
    )
    assert r.exit_code == ExitCode.USER_ERROR.value


def test_invalid_subcommand_rejected() -> None:
    r = runner.invoke(app, ["nuke-everything"])
    assert r.exit_code != ExitCode.SUCCESS.value
