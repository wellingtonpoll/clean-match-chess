"""`cleanmatch audit-username` subcommand (T068)."""

from __future__ import annotations

import sys

from analysis_core.ingest.chesscom_client import ChesscomClient, ChesscomError
from analysis_core.ingest.pgn_loader import (
    PgnValidationError,
    is_eligible_for_scoring,
    load_pgn_text,
)
from analysis_core.pipeline.run import run_username_batch
from shared_types.game import Game, PlayerColor

from cleanmatch_cli.output.exit_codes import ExitCode
from cleanmatch_cli.output.renderers import OutputFormat, render


def execute(
    username: str,
    *,
    platform: str,
    count: int,
    time_control: str | None,
    output: str,
    engine_path: str | None = None,
    engine_image: str | None = None,
    book_path: str | None = None,
    no_cache: bool = False,
) -> ExitCode:
    if platform != "chesscom":
        sys.stderr.write(f"error: --platform {platform!r} not supported in MVP; use 'chesscom'.\n")
        return ExitCode.USER_ERROR

    tc_filter = _parse_time_controls(time_control)
    if tc_filter is None and time_control is not None:
        return ExitCode.USER_ERROR

    try:
        with ChesscomClient() as client:
            fetched = client.fetch_recent_games(
                username,
                count=count,
                time_controls=tc_filter or None,
            )
    except ChesscomError as exc:
        sys.stderr.write(f"error: chess.com fetch failed: {exc}\n")
        return ExitCode.UPSTREAM_ERROR

    games: list[Game] = []
    for f in fetched:
        try:
            game = load_pgn_text(f.pgn, source="chesscom")
        except PgnValidationError:
            continue
        if not is_eligible_for_scoring(game):
            continue
        games.append(game)

    if not games:
        sys.stderr.write(f"error: no eligible games found for {username!r} on {platform}.\n")
        return ExitCode.USER_ERROR

    run = run_username_batch(
        username,
        tuple(games),
        subject=PlayerColor.WHITE,
        engine_path=engine_path or None,
        engine_image=engine_image or None,
        book_path=book_path,
        platform=platform,
        no_cache=no_cache,
    )

    fmt = OutputFormat(output)
    profile = run.account_profile
    payload = {
        "username": username,
        "platform": platform,
        "games_audited": profile.games_audited if profile else 0,
        "aggregate_score": (profile.aggregate_score.score if profile else 0.0),
        "risk_level": (profile.aggregate_score.risk_level.value if profile else "low"),
        "dominant_signals": (list(profile.aggregate_score.dominant_signals) if profile else []),
        "cross_game_patterns": ([p.name for p in profile.cross_game_patterns] if profile else []),
    }
    render(payload, fmt)
    return ExitCode.SUCCESS


def _parse_time_controls(raw: str | None) -> tuple[str, ...] | None:
    """Parse --time-control. Returns the tuple, () if unset, None on invalid."""
    if raw is None:
        return ()
    valid = {"bullet", "blitz", "rapid", "classical", "correspondence"}
    parts = tuple(p.strip() for p in raw.split(",") if p.strip())
    bad = [p for p in parts if p not in valid]
    if bad:
        sys.stderr.write(
            f"error: --time-control values invalid: {','.join(bad)} "
            f"(valid: {','.join(sorted(valid))}).\n"
        )
        return None
    return parts
