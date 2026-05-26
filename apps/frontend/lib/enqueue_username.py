#!/usr/bin/env python3
"""Fetch a username's recent chess.com games + enqueue an audit_job per game.

Called by Next.js `POST /api/audit-username`. The frontend then polls each
returned `job_id` via `GET /api/audit/[job_id]`.

Input (stdin JSON):
  {"username": "quaiada", "platform": "chesscom", "count": 10, "offset": 0}

Output (stdout JSON):
  {"jobs": [
    {"idx": 0, "job_id": "<uuid>", "headers": {...}, "ply_count": 36},
    {"idx": 1, "error": "too_short", "headers": {...}}, ...
  ]}

Errors during chess.com fetch return `{"error": "..."}`, exit 1.
Per-game enqueue errors are emitted inside the `jobs` list with an `error`
key so the frontend can render them without breaking the batch.
"""

from __future__ import annotations

import io
import json
import sys

sys.path.insert(0, "/home/mestre/Documents/repositories/clean-match-chess")

import chess.pgn
from analysis_core.db.audit_jobs import enqueue
from analysis_core.db.session import get_session_factory, init_engine
from analysis_core.ingest.chesscom_client import ChesscomClient, ChesscomError
from analysis_core.ingest.pgn_loader import is_eligible_for_scoring, load_pgn_text


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid JSON: {e}"}), flush=True)
        return 1

    username = payload.get("username", "").strip()
    platform = payload.get("platform", "chesscom")
    count = int(payload.get("count", 10))
    offset = int(payload.get("offset", 0))

    if not username:
        print(json.dumps({"error": "username required"}), flush=True)
        return 1
    if platform != "chesscom":
        print(json.dumps({"error": f"platform {platform!r} not supported"}), flush=True)
        return 1

    init_engine()
    factory = get_session_factory()
    if factory is None:
        print(json.dumps({"error": "DATABASE_URL not configured"}), flush=True)
        return 1

    try:
        with ChesscomClient() as client:
            fetched = client.fetch_recent_games(username, count=count + offset)
    except ChesscomError as e:
        print(json.dumps({"error": str(e)}), flush=True)
        return 1

    batch = fetched[offset : offset + count]
    if not batch:
        print(json.dumps({"jobs": []}), flush=True)
        return 0

    results: list[dict[str, object]] = []
    for i, fetched_game in enumerate(batch):
        idx = offset + i
        try:
            pgn_game = chess.pgn.read_game(io.StringIO(fetched_game.pgn))
            headers: dict[str, str] = dict(pgn_game.headers) if pgn_game else {}
            game = load_pgn_text(fetched_game.pgn, source="chesscom")
            if not is_eligible_for_scoring(game):
                results.append({"idx": idx, "error": "too_short", "headers": headers})
                continue
            # Subject is the requested username (whichever side they played).
            subject_color = (
                "white" if headers.get("White", "").lower() == username.lower() else "black"
            )
            with factory() as session:
                with session.begin():
                    job_id = enqueue(
                        session,
                        pgn_text=fetched_game.pgn,
                        subject_color=subject_color,
                    )
            results.append(
                {
                    "idx": idx,
                    "job_id": str(job_id),
                    "headers": headers,
                    "ply_count": game.ply_count,
                }
            )
        except Exception as e:
            results.append({"idx": idx, "error": f"{type(e).__name__}: {e}"})

    print(json.dumps({"jobs": results}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
