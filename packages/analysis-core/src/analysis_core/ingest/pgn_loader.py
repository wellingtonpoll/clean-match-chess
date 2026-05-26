"""PGN ingestion (FR-001, FR-003).

Parses a PGN string or file into a typed `Game` record, computing a
canonical SHA256 over the normalized PGN (whitespace-stripped, headers
sorted) so the same logical game always produces the same id.

Errors are raised as `PgnValidationError`. The CLI catches this and
maps to exit code 1 (USER_ERROR).
"""

from __future__ import annotations

import hashlib
import io
import re
import uuid
from pathlib import Path
from typing import Final

import chess
import chess.pgn
from shared_types.game import (
    Game,
    Move,
    MoveClassification,
    PlayerColor,
    PlayerRef,
    Result,
    TimeControl,
    TimeControlCategory,
)

PLY_MIN_FOR_SCORING: Final[int] = 10


class PgnValidationError(ValueError):
    """Raised when a PGN cannot be parsed or fails schema validation."""


_PGN_HEADER_RE = re.compile(r'^\s*\[\s*\w+\s+"[^"]*"\s*\]', re.MULTILINE)


def load_pgn_text(pgn: str, *, source: str = "paste") -> Game:
    """Parse a PGN string into a typed `Game`."""
    if not pgn.strip():
        raise PgnValidationError("empty PGN")
    if not _PGN_HEADER_RE.search(pgn):
        raise PgnValidationError("PGN has no valid header tags")

    game_node = chess.pgn.read_game(io.StringIO(pgn))
    if game_node is None:
        raise PgnValidationError("PGN did not parse")

    errors = game_node.errors
    if errors:
        first = errors[0]
        raise PgnValidationError(f"PGN parse error: {first}") from first

    variant = game_node.headers.get("Variant", "Standard")
    if variant and variant.lower() not in {"standard", ""}:
        raise PgnValidationError(f"unsupported variant: {variant!r}; MVP supports 'standard' only")

    headers = dict(game_node.headers)
    result = _parse_result(headers.get("Result", "*"))
    time_control = _parse_time_control(headers.get("TimeControl", "-"))
    players = _parse_players(headers)
    eco = headers.get("ECO")

    moves = tuple(_extract_moves(game_node, time_control))
    ply_count = len(moves)
    pgn_sha256 = _canonical_sha256(pgn, headers)

    return Game(
        id=uuid.uuid4().hex,
        pgn_sha256=pgn_sha256,
        source=source,
        headers=headers,
        players=players,
        result=result,
        time_control=time_control,
        eco=eco,
        ply_count=ply_count,
        moves=moves,
    )


def load_pgn_path(path: Path, *, source: str = "file") -> Game:
    """Parse a PGN file by path."""
    if not path.is_file():
        raise PgnValidationError(f"PGN file not found: {path}")
    return load_pgn_text(path.read_text(), source=source)


def is_eligible_for_scoring(game: Game) -> bool:
    """Spec edge case: games shorter than PLY_MIN_FOR_SCORING are ineligible."""
    return game.ply_count >= PLY_MIN_FOR_SCORING


def _parse_result(raw: str) -> Result:
    try:
        return Result(raw)
    except ValueError:
        return Result.UNKNOWN


def _parse_time_control(raw: str) -> TimeControl:
    base, increment = _split_tc(raw)
    return TimeControl(
        raw=raw,
        category=_classify_tc(base, increment),
        base_seconds=base,
        increment_seconds=increment,
    )


def _split_tc(raw: str) -> tuple[int | None, int | None]:
    if not raw or raw == "-":
        return None, None
    if "+" in raw:
        head, tail = raw.split("+", 1)
        return _maybe_int(head), _maybe_int(tail)
    return _maybe_int(raw), 0


def _maybe_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _classify_tc(base: int | None, increment: int | None) -> TimeControlCategory:
    if base is None:
        return TimeControlCategory.CORRESPONDENCE
    bonus = (increment or 0) * 40
    total = base + bonus
    if total < 180:
        return TimeControlCategory.BULLET
    if total < 600:
        return TimeControlCategory.BLITZ
    if total < 1800:
        return TimeControlCategory.RAPID
    return TimeControlCategory.CLASSICAL


def _parse_players(headers: dict[str, str]) -> tuple[PlayerRef, PlayerRef]:
    white = PlayerRef(
        color=PlayerColor.WHITE,
        username=headers.get("White") or None,
        display_name=headers.get("White") or None,
        rating=_maybe_int(headers.get("WhiteElo", "")),
    )
    black = PlayerRef(
        color=PlayerColor.BLACK,
        username=headers.get("Black") or None,
        display_name=headers.get("Black") or None,
        rating=_maybe_int(headers.get("BlackElo", "")),
    )
    return white, black


def _extract_moves(game_node: chess.pgn.Game, time_control: TimeControl) -> list[Move]:
    """Walk the game tree, building one Move per ply with timing parsed from `[%clk]`.

    Time accounting (FR-001 / FR-002):
      * Per-side prior_clock_ms starts at `time_control.base_seconds * 1000`
        (or None when TC unknown — disables timing for that side).
      * Each ply's comment is searched for `[%clk H:MM:SS(.s)]`; if present,
        `time_spent_ms = max(0, prior_clock_ms - current_clock_ms + increment_ms)`.
        The increment is added BACK because chess.com / Lichess emit the
        clock AFTER the increment has already been credited.
      * If a ply's comment has no clock, `time_spent_ms = None` for that ply
        (we don't extrapolate). prior_clock for that side stays whatever
        it was before — the next clocked ply still produces a valid delta.

    Examples (10+0, side W, after 1. e4 with [%clk 0:09:55]):
      * delta = 600_000 - 595_000 + 0 = 5000 ms.
    With increment 5 (`600+5`) and the same clock comment:
      * Lichess / chess.com show clock AFTER increment added, so
        prior=600000 → current=595000 means 10s spent, then +5s back =
        delta = 5000 + 5000 = 10_000 ms. Capped at 0.
    """
    from analysis_core.ingest._clock_parser import parse_clock_ms

    base = time_control.base_seconds
    increment_ms = (time_control.increment_seconds or 0) * 1000
    initial_clock_ms: int | None = base * 1000 if base else None

    prior_clock: dict[PlayerColor, int | None] = {
        PlayerColor.WHITE: initial_clock_ms,
        PlayerColor.BLACK: initial_clock_ms,
    }

    board = game_node.board()
    moves: list[Move] = []
    node: chess.pgn.GameNode = game_node
    ply = 0
    while node.variations:
        next_node = node.variations[0]
        assert next_node.move is not None
        san = board.san(next_node.move)
        uci = next_node.move.uci()
        side = PlayerColor.WHITE if board.turn else PlayerColor.BLACK

        comment = next_node.comment or ""
        current_clock_ms = parse_clock_ms(comment)
        time_spent_ms: int | None = None
        if current_clock_ms is not None and prior_clock[side] is not None:
            prev = prior_clock[side]
            assert prev is not None  # narrowed by guard above
            delta = prev - current_clock_ms + increment_ms
            time_spent_ms = max(0, delta)
            prior_clock[side] = current_clock_ms
        elif current_clock_ms is not None:
            # First clocked move for this side without a known initial — just
            # record the clock so the next ply can compute a delta.
            prior_clock[side] = current_clock_ms

        moves.append(
            Move(
                ply=ply,
                san=san,
                uci=uci,
                played_by=side,
                time_spent_ms=time_spent_ms,
                eval_delta_cp=0,
                classification=MoveClassification.GOOD,
                signal_contributions=(),
            )
        )
        board.push(next_node.move)
        node = next_node
        ply += 1
    return moves


def _canonical_sha256(pgn: str, headers: dict[str, str]) -> str:
    canonical_headers = "\n".join(f'[{k} "{v}"]' for k, v in sorted(headers.items()))
    movetext = pgn.split("\n\n", 1)[-1].strip() if "\n\n" in pgn else pgn.strip()
    payload = (canonical_headers + "\n\n" + movetext + "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
