#!/usr/bin/env python3
"""Streaming game analyzer — outputs JSONL to stdout, one line per completed game."""
import sys, json, concurrent.futures
sys.path.insert(0, '/home/mestre/Documents/repositories/clean-match-chess')

# The script receives args: username platform count offset
# platform is either "chesscom" or "lichess" (lichess not supported yet → error)

from analysis_core.ingest.chesscom_client import ChesscomClient, ChesscomError
from analysis_core.ingest.pgn_loader import load_pgn_text, is_eligible_for_scoring
from analysis_core.pipeline.run import run_single_game
from shared_types.game import PlayerColor, Game


def analyze_game(idx: int, pgn: str, headers: dict) -> dict:
    try:
        game: Game = load_pgn_text(pgn, source="chesscom")
        if not is_eligible_for_scoring(game):
            return {"idx": idx, "error": "too_short", "headers": headers}
        run = run_single_game(game)
        score = run.score.score if run.score else 0.0
        risk = run.score.risk_level.value if run.score else "low"
        ci = list(run.score.confidence_interval) if run.score else [0.0, 1.0]
        signals = list(run.score.dominant_signals) if run.score else []
        return {
            "idx": idx,
            "run_id": run.id,
            "score": score,
            "risk_level": risk,
            "confidence_interval": ci,
            "dominant_signals": signals,
            "headers": headers,
            "ply_count": game.ply_count,
        }
    except Exception as e:
        return {"idx": idx, "error": str(e), "headers": headers}


def main():
    username = sys.argv[1]
    platform = sys.argv[2] if len(sys.argv) > 2 else "chesscom"
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    offset = int(sys.argv[4]) if len(sys.argv) > 4 else 0

    if platform != "chesscom":
        print(json.dumps({"error": f"platform '{platform}' not supported yet"}), flush=True)
        sys.exit(1)

    try:
        with ChesscomClient() as client:
            fetched = client.fetch_recent_games(username, count=count + offset)
    except ChesscomError as e:
        print(json.dumps({"error": str(e)}), flush=True)
        sys.exit(1)

    batch = fetched[offset:offset + count]
    if not batch:
        print(json.dumps({"error": "no_games"}), flush=True)
        sys.exit(0)

    # Parse headers before submitting to threads
    import chess.pgn, io
    tasks = []
    for i, f in enumerate(batch):
        pgn_game = chess.pgn.read_game(io.StringIO(f.pgn))
        headers = dict(pgn_game.headers) if pgn_game else {}
        tasks.append((offset + i, f.pgn, headers))

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(analyze_game, idx, pgn, hdrs): idx
                   for idx, pgn, hdrs in tasks}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
