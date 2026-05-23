"""Per-position engine analysis (FR-004).

Defines the `Analyzer` Protocol: anything that, given a board, returns
top-N candidate moves + an evaluation. Two implementations live here:
- `StaticAnalyzer`: deterministic, no Stockfish required. Returns the
  first legal move with eval_cp=0. Used as the MVP fallback when no
  bundled engine exists and by unit tests.
- `EngineAnalyzer`: real Stockfish via python-chess (MVP US1 surface;
  exercised by the integration test marked `@slow`).

In US1 unit tests, prefer `StaticAnalyzer` to keep tests hermetic.
"""

from __future__ import annotations

from typing import Final, Protocol

import chess
from shared_types.game import CandidateMove, ComplexityScore, PlayerColor, Position

MAX_MULTIPV: Final[int] = 5


class Analyzer(Protocol):
    """Anything that can produce a `Position` record from a board state."""

    def analyse(self, board: chess.Board, ply: int) -> Position: ...


class StaticAnalyzer:
    """Deterministic analyzer used in MVP tests + as offline fallback."""

    def __init__(self, depth: int = 18, multipv: int = MAX_MULTIPV) -> None:
        self._depth = depth
        self._multipv = max(1, min(multipv, MAX_MULTIPV))

    def analyse(self, board: chess.Board, ply: int) -> Position:
        legal = list(board.legal_moves)
        top: list[CandidateMove] = []
        for rank, move in enumerate(legal[: self._multipv], start=1):
            top.append(
                CandidateMove(
                    san=board.san(move),
                    uci=move.uci(),
                    eval_cp=0,
                    mate_in=None,
                    pv=(board.san(move),),
                    rank=rank,
                )
            )
        side = PlayerColor.WHITE if board.turn else PlayerColor.BLACK
        is_only = len(legal) == 1
        complexity = ComplexityScore(
            branching_factor=float(len(legal)),
            eval_volatility=0.0,
            tactical_density=0.0,
            move_ambiguity=1.0 / max(1, len(legal)),
            composite=min(1.0, len(legal) / 40.0),
        )
        return Position(
            ply=ply,
            fen=board.fen(),
            side_to_move=side,
            eval_cp=0,
            mate_in=None,
            top_moves=tuple(top),
            complexity=complexity,
            is_critical=is_only or board.is_check(),
            is_only_move=is_only,
            is_book=False,
        )
