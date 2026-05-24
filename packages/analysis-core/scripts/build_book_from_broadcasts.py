"""Build a Polyglot opening book from a Lichess broadcast PGN archive.

One-shot maintainer script for feature 005 US2. Replaces the Phase 1
synthetic stub with a real master-game-derived book.

Source dataset: ``https://database.lichess.org/broadcast/lichess_db_broadcast_<YYYY-MM>.pgn.zst``
Source license: CC-BY-SA 4.0 (per ``database.lichess.org``).

Usage:

    uv run python packages/analysis-core/scripts/build_book_from_broadcasts.py \\
        --input /path/to/broadcast.pgn \\
        --output packages/analysis-core/data/opening_book.bin \\
        --max-ply 16 \\
        --min-weight 2

Polyglot binary format: 16-byte entries (u64 zobrist + u16 move + u16 weight
+ u32 learn), big-endian, sorted ascending by (key, weight desc).
Reference: http://hgm.nubati.net/book_format.html
"""

from __future__ import annotations

import argparse
import io
import struct
import sys
from collections import defaultdict
from pathlib import Path
from typing import Final

import chess
import chess.pgn
import chess.polyglot

_PROMOTION_BITS: Final[dict[int, int]] = {
    chess.KNIGHT: 1,
    chess.BISHOP: 2,
    chess.ROOK: 3,
    chess.QUEEN: 4,
}


def encode_move(move: chess.Move) -> int:
    """Encode a python-chess Move as a 16-bit Polyglot move integer.

    Bits 0-2  to-file
    Bits 3-5  to-rank
    Bits 6-8  from-file
    Bits 9-11 from-rank
    Bits 12-14 promotion piece (1=N, 2=B, 3=R, 4=Q; 0 = none)
    """
    to_file = chess.square_file(move.to_square)
    to_rank = chess.square_rank(move.to_square)
    from_file = chess.square_file(move.from_square)
    from_rank = chess.square_rank(move.from_square)
    promo = _PROMOTION_BITS.get(move.promotion or 0, 0)
    return to_file | (to_rank << 3) | (from_file << 6) | (from_rank << 9) | (promo << 12)


def aggregate_entries(
    pgn_path: Path,
    *,
    max_ply: int,
    min_weight: int,
) -> dict[tuple[int, int], int]:
    """Walk every game in ``pgn_path`` and tally (zobrist, move_code) -> count.

    Filters: keep only entries with ``weight >= min_weight``.
    """
    counts: dict[tuple[int, int], int] = defaultdict(int)
    games_scanned = 0
    with pgn_path.open(encoding="utf-8", errors="replace") as fh:
        while True:
            game = chess.pgn.read_game(fh)
            if game is None:
                break
            if game.headers.get("Variant", "Standard").lower() not in {"", "standard"}:
                continue
            board = game.board()
            for ply, move in enumerate(game.mainline_moves()):
                if ply >= max_ply:
                    break
                key = chess.polyglot.zobrist_hash(board)
                code = encode_move(move)
                counts[(key, code)] += 1
                board.push(move)
            games_scanned += 1
            if games_scanned % 5000 == 0:
                print(f"  scanned {games_scanned} games...", file=sys.stderr)
    print(f"  total games scanned: {games_scanned}", file=sys.stderr)
    return {k: w for k, w in counts.items() if w >= min_weight}


def write_polyglot(
    entries: dict[tuple[int, int], int],
    *,
    output: Path,
) -> int:
    """Write entries to a Polyglot .bin file. Returns entry count."""
    # Polyglot requires entries sorted by key ascending, then by weight
    # descending so the highest-weight move for a key is picked first by
    # readers that take the first entry.
    sorted_entries = sorted(entries.items(), key=lambda kv: (kv[0][0], -kv[1]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as fh:
        for (key, code), weight in sorted_entries:
            # Weights are clamped to u16 max so we don't overflow.
            w = min(weight, 0xFFFF)
            fh.write(struct.pack(">QHHI", key, code, w, 0))
    return len(sorted_entries)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, required=True, help="Decompressed broadcast PGN file."
    )
    parser.add_argument("--output", type=Path, required=True, help="Target .bin file.")
    parser.add_argument("--max-ply", type=int, default=16)
    parser.add_argument("--min-weight", type=int, default=2)
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2

    print(f"reading {args.input}", file=sys.stderr)
    entries = aggregate_entries(args.input, max_ply=args.max_ply, min_weight=args.min_weight)
    print(f"  kept {len(entries)} entries (min_weight={args.min_weight})", file=sys.stderr)

    n = write_polyglot(entries, output=args.output)
    print(f"  wrote {n} entries to {args.output}", file=sys.stderr)
    print(f"  size: {args.output.stat().st_size} bytes", file=sys.stderr)

    # Quick self-check: re-read and probe the standard starting position.
    with chess.polyglot.open_reader(args.output) as reader:
        start = chess.Board()
        hits = list(reader.find_all(start))
        print(f"  start-position entries: {len(hits)}", file=sys.stderr)
        if hits:
            top = max(hits, key=lambda e: e.weight)
            print(f"  most-popular first move: {top.move} (weight {top.weight})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# Sanity: confirm the module imports cleanly under mypy --strict by referencing
# io explicitly (kept for potential future stdin streaming).
_ = io.StringIO
