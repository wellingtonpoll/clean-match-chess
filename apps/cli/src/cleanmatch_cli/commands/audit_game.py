"""`cleanmatch audit-game` subcommand (T058)."""

from __future__ import annotations

import sys
from pathlib import Path

from analysis_core.ingest.pgn_loader import (
    PgnValidationError,
    is_eligible_for_scoring,
    load_pgn_path,
    load_pgn_text,
)
from analysis_core.pipeline.run import run_single_game
from shared_types.game import PlayerColor

from cleanmatch_cli.output.exit_codes import ExitCode
from cleanmatch_cli.output.renderers import OutputFormat, render


def execute(
    input_arg: str,
    *,
    subject: str | None,
    output: str,
    engine_path: str | None = None,
    engine_image: str | None = None,
    book_path: str | None = None,
    no_cache: bool = False,
) -> ExitCode:
    """Run the single-game audit. Returns the exit code.

    ``no_cache`` (feature 008): when True, bypasses both the Postgres
    cache lookup and the persist step.
    """
    try:
        game = _load_game(input_arg)
    except PgnValidationError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return ExitCode.USER_ERROR
    except FileNotFoundError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return ExitCode.USER_ERROR

    if not is_eligible_for_scoring(game):
        sys.stderr.write(
            f"error: game has {game.ply_count} plies; minimum 10 required for scoring.\n"
        )
        return ExitCode.USER_ERROR

    color = _parse_subject(subject)
    run = run_single_game(
        game,
        subject=color,
        engine_path=engine_path or None,
        engine_image=engine_image or None,
        book_path=book_path,
        no_cache=no_cache,
    )

    fmt = OutputFormat(output)
    payload = {
        "run_id": run.id,
        "subject": {
            "color": run.subject.color.value,
            "username": run.subject.username or "",
        },
        "score": run.score.score if run.score else 0.0,
        "risk_level": run.score.risk_level.value if run.score else "low",
        "confidence_interval": list(run.score.confidence_interval) if run.score else [0.0, 0.0],
        "dominant_signals": list(run.score.dominant_signals) if run.score else [],
    }
    render(payload, fmt)
    return ExitCode.SUCCESS


def _load_game(input_arg: str):  # type: ignore[no-untyped-def]
    if input_arg == "-":
        return load_pgn_text(sys.stdin.read())
    return load_pgn_path(Path(input_arg))


def _parse_subject(value: str | None) -> PlayerColor:
    if value is None:
        return PlayerColor.WHITE
    lowered = value.strip().lower()
    if lowered not in {"white", "black"}:
        raise ValueError(f"--subject must be 'white' or 'black'; got {value!r}")
    return PlayerColor(lowered)
