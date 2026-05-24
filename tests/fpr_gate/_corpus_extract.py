"""One-shot helper to extract well-formed PGN fixtures from a Lichess broadcast
archive into ``tests/fixtures/corpora/clean/``.

This is a maintainer utility, not pytest-collected. Invoke with:

    uv run python -m tests.fpr_gate._corpus_extract \\
        --input /tmp/broadcast.pgn \\
        --output-dir tests/fixtures/corpora/clean \\
        --target-count 50 \\
        --source-archive lichess_db_broadcast_2025-04

Each emitted PGN is paired with a ``.provenance.json`` sidecar matching
``contracts/provenance.schema.json``: ``label="clean"``,
``label_confidence="high"`` (OTB broadcast, arbiter-monitored).
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import chess.pgn

_FILENAME_SAFE_RE = re.compile(r"[^a-z0-9_\-]+")
_REQUIRED_HEADERS = ("Event", "White", "Black", "Result", "WhiteElo", "BlackElo")


def _safe_token(text: str) -> str:
    token = _FILENAME_SAFE_RE.sub("_", text.lower()).strip("_")
    return token[:40] or "anon"


def _filename(stem: str, index: int) -> str:
    return f"{stem}_{index:03d}.pgn"


def _is_well_formed(game: chess.pgn.Game) -> bool:
    if game.errors:
        return False
    headers = game.headers
    if any(not headers.get(h, "").strip() or headers.get(h) == "?" for h in _REQUIRED_HEADERS):
        return False
    # Reject incomplete results.
    if headers.get("Result") not in {"1-0", "0-1", "1/2-1/2"}:
        return False
    # Require >= 40 ply and standard variant.
    if headers.get("Variant", "Standard").lower() not in {"", "standard"}:
        return False
    plies = sum(1 for _ in game.mainline_moves())
    return plies >= 40


def iter_well_formed(input_path: Path) -> Iterator[chess.pgn.Game]:
    with input_path.open(encoding="utf-8", errors="replace") as fh:
        while True:
            game = chess.pgn.read_game(fh)
            if game is None:
                return
            if _is_well_formed(game):
                yield game


def _render_pgn(game: chess.pgn.Game) -> str:
    buf = io.StringIO()
    exporter = chess.pgn.FileExporter(buf, headers=True, comments=False, variations=False)
    game.accept(exporter)
    return buf.getvalue()


def _provenance_json(*, source_archive: str, white: str, black: str, event: str) -> str:
    return (
        json.dumps(
            {
                "source": f"https://database.lichess.org/broadcast/{source_archive}.pgn.zst",
                "retrieved_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "label": "clean",
                "label_confidence": "high",
                "notes": (
                    f"OTB broadcast game ({event}) — arbiter-monitored at play time. "
                    f"Source: Lichess broadcast archive {source_archive} (CC-BY-SA 4.0). "
                    f"Players: {white} vs {black}."
                ),
            },
            indent=2,
        )
        + "\n"
    )


def extract(
    *,
    input_path: Path,
    output_dir: Path,
    target_count: int,
    source_archive: str,
    keep_strides: int,
) -> int:
    """Walk ``input_path``, emit up to ``target_count`` well-formed games to
    ``output_dir``. Returns the actual number emitted.

    ``keep_strides``: take every Nth well-formed game to diversify across the
    archive (avoid back-to-back games from the same tournament round).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    emitted = 0
    seen = 0
    for game in iter_well_formed(input_path):
        seen += 1
        if seen % keep_strides != 0:
            continue
        if emitted >= target_count:
            break
        event = game.headers.get("Event", "event")
        white = game.headers.get("White", "white")
        black = game.headers.get("Black", "black")
        stem = _safe_token(f"{event}_{white}_{black}")
        filename = _filename(stem, emitted)
        pgn_path = output_dir / filename
        pgn_path.write_text(_render_pgn(game), encoding="utf-8")
        prov_path = pgn_path.with_suffix(".provenance.json")
        prov_path.write_text(
            _provenance_json(
                source_archive=source_archive,
                white=white,
                black=black,
                event=event,
            ),
            encoding="utf-8",
        )
        emitted += 1
    return emitted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target-count", type=int, default=50)
    parser.add_argument("--source-archive", type=str, required=True)
    parser.add_argument("--keep-strides", type=int, default=37)
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2

    n = extract(
        input_path=args.input,
        output_dir=args.output_dir,
        target_count=args.target_count,
        source_archive=args.source_archive,
        keep_strides=args.keep_strides,
    )
    print(f"emitted {n} PGNs + sidecars to {args.output_dir}", file=sys.stderr)
    return 0 if n >= args.target_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
