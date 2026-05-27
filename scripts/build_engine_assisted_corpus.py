#!/usr/bin/env python3
"""chess.com banned-account corpus crawler (feature 013).

BFS starting from one or more seed usernames. For each visited user,
queries `/pub/player/{u}` to read the `status` field. Users with
`status LIKE 'closed:fair_play%'` produce labeled-cheat corpus rows:
the script pulls their N most-recent rated games as PGN and writes
them under `tests/fixtures/corpora/engine_assisted/<username>_<game_id>.pgn`
with a sibling `.provenance.json` (matches feature 005 schema).

State persists to the `chesscom_crawl_status` table so a multi-hour
crawl can be resumed via `--resume` without re-checking everyone.

Rate limit: chess.com public API caps unauthenticated traffic around
30 req/min. Script sleeps 2 s between profile checks; resumes from DB
state so re-runs don't repeat work.

Usage:
    # Fresh run, single seed, default depth=2, target 100 PGNs.
    uv run python scripts/build_engine_assisted_corpus.py --seed quaiada

    # Custom seeds + depth + target.
    uv run python scripts/build_engine_assisted_corpus.py \\
        --seed quaiada --seed jeujack --depth 1 --target-pgns 50

    # Resume mid-crawl.
    uv run python scripts/build_engine_assisted_corpus.py --resume

Environment:
    DATABASE_URL — required.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import os
import re
import sys
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

import chess.pgn

sys.path.insert(0, "/home/mestre/Documents/repositories/clean-match-chess")

from analysis_core.db.chesscom_crawl import (
    crawl_summary,
    increment_games_pulled,
    is_already_visited,
    list_banned,
    record_visit,
)
from analysis_core.db.session import get_session_factory, init_engine
from analysis_core.ingest.chesscom_client import ChesscomClient, ChesscomError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("corpus_crawler")

REPO_ROOT = Path("/home/mestre/Documents/repositories/clean-match-chess")
CORPUS_DIR = REPO_ROOT / "tests" / "fixtures" / "corpora" / "engine_assisted"

_REQUEST_SLEEP_S = 2.0  # ~30 req/min budget under chess.com public limit.


def _safe_filename(s: str) -> str:
    """Reduce username/game_id to a path-safe slug."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", s)


def _extract_game_id(pgn_text: str) -> str | None:
    """Pull game id from the `[Link "https://www.chess.com/game/live/12345"]` header."""
    m = re.search(r'\[Link\s+"https://www\.chess\.com/game/(?:live|daily)/(\d+)"\]', pgn_text)
    if m:
        return m.group(1)
    # Fallback: sha256 prefix.
    return hashlib.sha256(pgn_text.encode("utf-8")).hexdigest()[:16]


def _opponents_from_archive(games_raw: list[dict[str, object]], self_username: str) -> set[str]:
    """Collect every distinct opponent username from a month's games payload."""
    out: set[str] = set()
    me = self_username.lower()
    for entry in games_raw:
        white = entry.get("white", {})
        black = entry.get("black", {})
        if isinstance(white, dict) and isinstance(white.get("username"), str):
            u = white["username"]
            if u.lower() != me:
                out.add(u)
        if isinstance(black, dict) and isinstance(black.get("username"), str):
            u = black["username"]
            if u.lower() != me:
                out.add(u)
    return out


def _pull_user_games(
    client: ChesscomClient,
    username: str,
    *,
    per_user_limit: int,
) -> list[dict[str, object]]:
    """Fetch up to `per_user_limit` PGN entries for `username` (most recent first).

    Walks the archive list from the most recent month backwards.
    """
    archives_raw = client._fetch_archives(username)
    games: list[dict[str, object]] = []
    for archive_url in reversed(archives_raw):
        time.sleep(_REQUEST_SLEEP_S)
        try:
            url = archive_url.replace(client._base_url, "")
            payload = client._get_json(url)
        except ChesscomError as e:
            log.warning("archive.fetch_failed url=%s error=%s", archive_url, e)
            continue
        archive_games = payload.get("games")
        if not isinstance(archive_games, list):
            continue
        for g in archive_games:
            if isinstance(g, dict):
                games.append(g)
        if len(games) >= per_user_limit:
            break
    return games[:per_user_limit]


def _collect_opponents_for_user(
    client: ChesscomClient,
    username: str,
    *,
    months_back: int,
) -> set[str]:
    """Return the set of distinct opponent usernames seen across recent months."""
    archives_raw = client._fetch_archives(username)
    opps: set[str] = set()
    for archive_url in list(reversed(archives_raw))[:months_back]:
        time.sleep(_REQUEST_SLEEP_S)
        try:
            url = archive_url.replace(client._base_url, "")
            payload = client._get_json(url)
        except ChesscomError as e:
            log.warning("opponent.fetch_failed url=%s error=%s", archive_url, e)
            continue
        archive_games = payload.get("games")
        if isinstance(archive_games, list):
            opps |= _opponents_from_archive(
                [g for g in archive_games if isinstance(g, dict)], username
            )
    return opps


def _write_game_to_corpus(
    *,
    username: str,
    pgn_text: str,
    profile_status: str,
) -> bool:
    """Write one PGN + provenance JSON. Returns True if a new file was written."""
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        parsed = chess.pgn.read_game(io.StringIO(pgn_text))
        headers = dict(parsed.headers) if parsed else {}
    except Exception:
        headers = {}
    game_id = _extract_game_id(pgn_text) or "unknown"
    fname = f"{_safe_filename(username)}_{_safe_filename(game_id)}"
    pgn_path = CORPUS_DIR / f"{fname}.pgn"
    prov_path = CORPUS_DIR / f"{fname}.provenance.json"
    if pgn_path.exists():
        return False
    pgn_path.write_text(pgn_text)
    prov_path.write_text(
        json.dumps(
            {
                "source": "chess.com",
                "retrieved_at": datetime.now(UTC).isoformat(),
                "label": "engine-assisted",
                "label_confidence": "high",
                "notes": (
                    f"chess.com pub API /pub/player/{username} reported "
                    f"status={profile_status!r}. Crawled by feature 013 corpus builder."
                ),
                "chesscom_username": username,
                "chesscom_game_id": game_id,
                "chesscom_headers": headers,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return True


def crawl(
    *,
    seeds: list[str],
    max_depth: int,
    target_pgns: int,
    per_user_limit: int,
    months_back: int,
    resume: bool,
) -> None:
    init_engine()
    factory = get_session_factory()
    if factory is None:
        raise SystemExit("DATABASE_URL not configured")

    if not resume:
        log.info(
            "starting fresh crawl from seeds=%s depth=%d target=%d", seeds, max_depth, target_pgns
        )
    else:
        log.info("resuming crawl from existing chesscom_crawl_status state")

    # BFS frontier: (username, depth, seed_for_record).
    frontier: deque[tuple[str, int, str]] = deque()
    for s in seeds:
        frontier.append((s, 0, s))

    with ChesscomClient() as client:
        # Initial PGN count from already-visited banned users.
        with factory() as session:
            already = crawl_summary(session)
        log.info(
            "start state: banned=%d total_visited=%d games_pulled=%d",
            already.get("banned", 0),
            already.get("total", 0),
            already.get("games_pulled", 0),
        )
        pulled_total = already.get("games_pulled", 0)

        while frontier and pulled_total < target_pgns:
            username, depth, seed = frontier.popleft()

            with factory() as session:
                if is_already_visited(session, username=username):
                    log.debug("skip.already_visited username=%s", username)
                    # Still expand frontier if it's banned + we haven't gone deep.
                    if depth < max_depth:
                        banned_rows = [r for r in list_banned(session) if r.username == username]
                        if banned_rows:
                            _enqueue_opponents(client, username, depth, seed, frontier, factory)
                    continue

            # Profile lookup.
            time.sleep(_REQUEST_SLEEP_S)
            try:
                profile = client.get_player_profile(username)
            except ChesscomError as e:
                log.warning("profile.fetch_failed username=%s error=%s", username, e)
                continue
            if profile is None:
                log.info("profile.not_found username=%s", username)
                continue
            status = str(profile.get("status", "unknown"))

            with factory() as session:
                with session.begin():
                    record_visit(
                        session,
                        username=username,
                        status=status,
                        depth_from_seed=depth,
                        seed_username=seed,
                        profile_json=profile,
                    )

            log.info("visit username=%s status=%s depth=%d", username, status, depth)

            if status.startswith("closed:fair_play"):
                # Banned account — pull games into corpus.
                try:
                    games = _pull_user_games(client, username, per_user_limit=per_user_limit)
                except ChesscomError as e:
                    log.warning("games.fetch_failed username=%s error=%s", username, e)
                    games = []
                written = 0
                for g in games:
                    if pulled_total >= target_pgns:
                        break
                    pgn = g.get("pgn")
                    if not isinstance(pgn, str) or not pgn.strip():
                        continue
                    if _write_game_to_corpus(
                        username=username, pgn_text=pgn, profile_status=status
                    ):
                        written += 1
                        pulled_total += 1
                if written:
                    with factory() as session:
                        with session.begin():
                            increment_games_pulled(session, username=username, by=written)
                log.info(
                    "corpus.added username=%s games=%d total=%d", username, written, pulled_total
                )

            # Frontier expansion for everyone we visited (up to max_depth).
            if depth < max_depth:
                _enqueue_opponents(
                    client, username, depth, seed, frontier, factory, months_back=months_back
                )

        with factory() as session:
            summary = crawl_summary(session)
        log.info(
            "DONE banned=%d total_visited=%d games_pulled=%d (target=%d)",
            summary["banned"],
            summary["total"],
            summary["games_pulled"],
            target_pgns,
        )


def _enqueue_opponents(
    client: ChesscomClient,
    username: str,
    depth: int,
    seed: str,
    frontier: deque[tuple[str, int, str]],
    factory: object,
    *,
    months_back: int = 3,
) -> None:
    """Pull opponent usernames from recent months and append unseen to frontier."""
    try:
        opponents = _collect_opponents_for_user(client, username, months_back=months_back)
    except ChesscomError as e:
        log.warning("opponents.fetch_failed username=%s error=%s", username, e)
        return
    with factory() as session:  # type: ignore[misc]
        for opp in sorted(opponents):
            if not is_already_visited(session, username=opp):
                frontier.append((opp, depth + 1, seed))
    log.info("frontier.expanded from=%s opponents=%d", username, len(opponents))


def main() -> int:
    p = argparse.ArgumentParser(description="chess.com banned-account corpus crawler")
    p.add_argument(
        "--seed",
        action="append",
        default=[],
        help="Seed username (may be passed multiple times). Default: ['quaiada']",
    )
    p.add_argument(
        "--depth",
        type=int,
        default=2,
        help="BFS depth. 0 = seeds only; 1 = seeds + opponents; 2 = +opponents-of-opponents.",
    )
    p.add_argument(
        "--target-pgns",
        type=int,
        default=100,
        help="Stop crawling once this many PGNs are in the corpus.",
    )
    p.add_argument(
        "--per-user-limit",
        type=int,
        default=20,
        help="Max PGNs to pull per banned user.",
    )
    p.add_argument(
        "--months-back",
        type=int,
        default=3,
        help="How many recent monthly archives to scan when collecting opponents.",
    )
    p.add_argument(
        "--resume",
        action="store_true",
        help="Skip already-visited users (default behavior; flag is for clarity).",
    )
    args = p.parse_args()

    seeds = args.seed or ["quaiada"]

    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL not set")

    crawl(
        seeds=seeds,
        max_depth=args.depth,
        target_pgns=args.target_pgns,
        per_user_limit=args.per_user_limit,
        months_back=args.months_back,
        resume=args.resume,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
