"""`cleanmatch show <run-id> [--ply N]` subcommand (T073, T076)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from analysis_core.pipeline.cache import cleanmatch_home
from shared_types.audit_run import AuditRun
from shared_types.game import Game, Position
from shared_types.score import SuspicionScore

from cleanmatch_cli.output.exit_codes import ExitCode
from cleanmatch_cli.output.ply_renderer import render_ply
from cleanmatch_cli.output.timeline_renderer import render_timeline


def execute(run_id: str, *, ply: int | None) -> ExitCode:
    run_dir = cleanmatch_home() / "runs" / run_id
    if not run_dir.is_dir():
        sys.stderr.write(f"error: run {run_id!r} not found under {run_dir}.\n")
        return ExitCode.USER_ERROR

    try:
        run = AuditRun.model_validate_json((run_dir / "run.json").read_text())
        game = Game.model_validate_json((run_dir / "game.json").read_text())
        score = SuspicionScore.model_validate_json((run_dir / "score.json").read_text())
        positions = tuple(
            Position.model_validate(p) for p in json.loads((run_dir / "positions.json").read_text())
        )
    except FileNotFoundError as exc:
        sys.stderr.write(f"error: run directory missing file: {exc}\n")
        return ExitCode.UPSTREAM_ERROR

    if ply is None:
        for line in render_timeline(run, game, positions, score):
            sys.stdout.write(line + "\n")
        return ExitCode.SUCCESS

    if ply < 0 or ply >= len(game.moves):
        sys.stderr.write(f"error: --ply {ply} out of range [0, {len(game.moves) - 1}].\n")
        return ExitCode.USER_ERROR

    move = game.moves[ply]
    position = positions[ply] if ply < len(positions) else positions[-1]
    lines, _invariant = render_ply(ply, move, position)
    for line in lines:
        sys.stdout.write(line + "\n")
    return ExitCode.SUCCESS


def _runs_root() -> Path:
    return cleanmatch_home() / "runs"
