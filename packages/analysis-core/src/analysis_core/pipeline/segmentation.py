"""Game segmentation into phases (FR-007).

Returns a tuple of `Segment` records covering the entire ply range. The
MVP rule set is deliberately coarse and deterministic:

- Opening: plies 0 .. min(book_end, 20)
- Middlegame: opening_end .. material_drop_ply
- Tactical: contiguous windows containing the most "critical" positions
- Conversion: material_drop_ply .. last_non_endgame_ply
- Endgame: <= 7 pieces on the board OR plies after move 50

`material_drop_ply` is the first ply where total piece count falls
below 24 (start) - 6 = 18.
"""

from __future__ import annotations

from shared_types.game import Position
from shared_types.signal import Phase, Regime, Segment, SignalAggregate

_OPENING_END_DEFAULT: int = 20
_MATERIAL_FLOOR: int = 18
_ENDGAME_PIECE_FLOOR: int = 14


def segment_game(positions: tuple[Position, ...]) -> tuple[Segment, ...]:
    if not positions:
        return ()

    ply_count = len(positions)
    opening_end = _opening_end_ply(positions)
    middlegame_end = _middlegame_end_ply(positions, opening_end)
    endgame_start = _endgame_start_ply(positions, middlegame_end)
    tactical_window = _tactical_window(positions, opening_end, endgame_start)

    segments: list[Segment] = []
    segments.append(_segment(Phase.OPENING, 0, opening_end))
    if opening_end < middlegame_end:
        segments.append(_segment(Phase.MIDDLEGAME, opening_end, middlegame_end))
    if tactical_window is not None:
        start, end = tactical_window
        segments.append(_segment(Phase.TACTICAL, start, end))
    if middlegame_end < endgame_start:
        segments.append(_segment(Phase.CONVERSION, middlegame_end, endgame_start))
    if endgame_start < ply_count:
        segments.append(_segment(Phase.ENDGAME, endgame_start, ply_count))
    return tuple(segments)


def _opening_end_ply(positions: tuple[Position, ...]) -> int:
    last_book = -1
    for idx, pos in enumerate(positions):
        if pos.is_book:
            last_book = idx
        else:
            break
    if last_book < 0:
        return min(_OPENING_END_DEFAULT, len(positions))
    return min(last_book + 1, _OPENING_END_DEFAULT, len(positions))


def _middlegame_end_ply(positions: tuple[Position, ...], opening_end: int) -> int:
    for idx in range(opening_end, len(positions)):
        if _piece_count(positions[idx].fen) <= _MATERIAL_FLOOR:
            return idx
    return len(positions)


def _endgame_start_ply(positions: tuple[Position, ...], middlegame_end: int) -> int:
    for idx in range(middlegame_end, len(positions)):
        if _piece_count(positions[idx].fen) <= _ENDGAME_PIECE_FLOOR:
            return idx
    return len(positions)


def _tactical_window(positions: tuple[Position, ...], lo: int, hi: int) -> tuple[int, int] | None:
    critical_indices = [i for i in range(lo, hi) if positions[i].is_critical]
    if not critical_indices:
        return None
    start = critical_indices[0]
    end = critical_indices[-1] + 1
    return start, end


def _segment(phase: Phase, start: int, end: int) -> Segment:
    return Segment(
        phase=phase,
        ply_range=(start, end),
        regime=Regime.UNDETERMINED,
        signals=(_segment_size_signal(start, end),),
        score_contribution=0.0,
    )


def _segment_size_signal(start: int, end: int) -> SignalAggregate:
    samples = max(0, end - start)
    return SignalAggregate(
        signal_name="segment-size",
        signal_version="0.1.0",
        mean=float(samples),
        weighted_mean=float(samples),
        samples=samples,
    )


def _piece_count(fen: str) -> int:
    board_part = fen.split(" ", 1)[0]
    return sum(1 for ch in board_part if ch.isalpha())
