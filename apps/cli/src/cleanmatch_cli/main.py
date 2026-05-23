"""Typer entry point for `cleanmatch`.

Phase 2 ships the surface (subcommands, flags, exit codes) but every
subcommand currently exits with USER_ERROR + a "not implemented yet"
message. Phase 3 (US1) implements `audit-game` first.
"""

from __future__ import annotations

import sys

import typer

from cleanmatch_cli.output.exit_codes import ExitCode
from cleanmatch_cli.output.logging import LogFormat, LogLevel, configure

app = typer.Typer(
    name="cleanmatch",
    help="Probabilistic fair-play audit for chess.com PGNs.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _root(
    log_format: LogFormat = typer.Option(LogFormat.PRETTY, "--log-format"),
    log_level: LogLevel = typer.Option(LogLevel.INFO, "--log-level"),
) -> None:
    configure(fmt=log_format, level=log_level)


def _not_implemented(name: str) -> None:
    sys.stderr.write(
        f"error: subcommand {name!r} not implemented yet (Phase 3 of feature 001).\n"
        "next: track progress in specs/001-fairplay-analysis/tasks.md.\n"
    )
    raise typer.Exit(code=ExitCode.USER_ERROR.value)


@app.command("audit-game")
def audit_game(
    input: str = typer.Argument(..., help="Path to a .pgn file or '-' for stdin."),
    subject: str | None = typer.Option(None, "--subject"),
    depth: int = typer.Option(18, "--depth", min=1),
    multipv: int = typer.Option(5, "--multipv", min=1),
    book: str | None = typer.Option(None, "--book"),
    output: str = typer.Option("human", "--output"),
    language: str = typer.Option("en", "--language"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Audit a single PGN (single-game probabilistic analysis)."""
    from cleanmatch_cli.commands.audit_game import execute

    code = execute(input, subject=subject, output=output)
    raise typer.Exit(code=code.value)


@app.command("audit-username")
def audit_username(
    username: str = typer.Argument(...),
    platform: str = typer.Option("chesscom", "--platform"),
    count: int = typer.Option(20, "--count", min=1),
    time_control: str | None = typer.Option(None, "--time-control"),
    depth: int = typer.Option(18, "--depth", min=1),
    multipv: int = typer.Option(5, "--multipv", min=1),
    book: str | None = typer.Option(None, "--book"),
    output: str = typer.Option("human", "--output"),
    language: str = typer.Option("en", "--language"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    max_concurrency: int | None = typer.Option(None, "--max-concurrency", min=1),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Audit a username's recent public games (batch)."""
    from cleanmatch_cli.commands.audit_username import execute

    code = execute(
        username,
        platform=platform,
        count=count,
        time_control=time_control,
        output=output,
    )
    raise typer.Exit(code=code.value)


@app.command("show")
def show(
    run_id: str = typer.Argument(...),
    game_index: int | None = typer.Argument(None),
    ply: int | None = typer.Option(None, "--ply", min=0),
    format: str = typer.Option("human", "--format"),
    language: str = typer.Option("en", "--language"),
) -> None:
    """Show timeline / per-move detail for a persisted run."""
    from cleanmatch_cli.commands.show import execute

    code = execute(run_id, ply=ply)
    raise typer.Exit(code=code.value)


@app.command("export")
def export(
    run_id: str = typer.Argument(...),
    format: str = typer.Option("bundle", "--format"),
    out: str | None = typer.Option(None, "--out"),
    language: str = typer.Option("en", "--language"),
    include_positions: bool = typer.Option(False, "--include-positions"),
) -> None:
    """Export an auditable report bundle for a persisted run."""
    from cleanmatch_cli.commands.export import execute

    code = execute(run_id, format_=format, out=out, language=language)
    raise typer.Exit(code=code.value)


if __name__ == "__main__":
    app()
