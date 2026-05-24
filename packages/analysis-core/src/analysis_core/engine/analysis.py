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

import statistics
from pathlib import Path
from typing import Final, Protocol

import chess
import chess.engine
from shared_types.game import CandidateMove, ComplexityScore, PlayerColor, Position

MAX_MULTIPV: Final[int] = 5
_MATE_SCORE_CP: Final[int] = 30_000


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


class EngineAnalyzer:
    """Real Stockfish analyzer via python-chess UCI driver.

    Must be used as a context manager — opens one engine process for
    the lifetime of the analysis run, then shuts it down cleanly.

        # Local binary
        with EngineAnalyzer("/usr/bin/stockfish") as a: ...

        # Containerized via Podman/Docker
        with EngineAnalyzer(["podman", "run", "--rm", "-i", "cleanmatch-stockfish:quick"]) as a: ...
    """

    def __init__(
        self,
        command: str | Path | list[str],
        *,
        depth: int = 18,
        multipv: int = MAX_MULTIPV,
    ) -> None:
        self._command: str | list[str] = (
            command if isinstance(command, list) else str(command)
        )
        self._depth = depth
        self._multipv = max(1, min(multipv, MAX_MULTIPV))
        self._engine: chess.engine.SimpleEngine | None = None

    # ── context manager ───────────────────────────────────────────────

    def __enter__(self) -> EngineAnalyzer:
        self._engine = chess.engine.SimpleEngine.popen_uci(self._command)
        # MultiPV is managed by python-chess — pass it to analyse(), not here.
        self._engine.configure({"Threads": 1, "Hash": 256})
        return self

    def __exit__(self, *exc: object) -> None:
        if self._engine is not None:
            self._engine.quit()
            self._engine = None

    # ── public API ────────────────────────────────────────────────────

    def analyse(self, board: chess.Board, ply: int) -> Position:
        if self._engine is None:
            raise RuntimeError("EngineAnalyzer must be used as a context manager")

        legal = list(board.legal_moves)
        side = PlayerColor.WHITE if board.turn else PlayerColor.BLACK
        is_only = len(legal) == 1

        if not legal:
            return _terminal_position(board, ply, side)

        limit = chess.engine.Limit(depth=self._depth)
        multipv = min(self._multipv, len(legal))

        info_list = self._engine.analyse(board, limit, multipv=multipv)
        if not isinstance(info_list, list):
            info_list = [info_list]

        top_moves = _build_candidates(info_list, board)
        complexity = _build_complexity(legal, top_moves)
        best_eval = top_moves[0].eval_cp if top_moves else 0
        best_mate = top_moves[0].mate_in if top_moves else None

        return Position(
            ply=ply,
            fen=board.fen(),
            side_to_move=side,
            eval_cp=best_eval,
            mate_in=best_mate,
            top_moves=tuple(top_moves),
            complexity=complexity,
            is_critical=is_only or board.is_check(),
            is_only_move=is_only,
            is_book=False,
        )


# ── helpers ───────────────────────────────────────────────────────────


def _build_candidates(
    info_list: list[chess.engine.InfoDict],
    board: chess.Board,
) -> list[CandidateMove]:
    candidates: list[CandidateMove] = []
    for rank, info in enumerate(info_list, start=1):
        pv = info.get("pv") or []
        if not pv:
            continue
        move = pv[0]
        score = info.get("score")
        eval_cp: int | None = None
        mate_in: int | None = None
        if score is not None:
            rel = score.relative
            mate_in = rel.mate()
            if mate_in is None:
                raw = rel.score(mate_score=_MATE_SCORE_CP)
                eval_cp = int(raw) if raw is not None else None
            else:
                eval_cp = _MATE_SCORE_CP if mate_in > 0 else -_MATE_SCORE_CP

        # Build SAN PV (best-effort; stop on illegal move)
        pv_sans: list[str] = []
        tmp = board.copy()
        for m in pv:
            try:
                pv_sans.append(tmp.san(m))
                tmp.push(m)
            except (ValueError, AssertionError):
                break

        candidates.append(
            CandidateMove(
                san=board.san(move),
                uci=move.uci(),
                eval_cp=eval_cp,
                mate_in=mate_in,
                pv=tuple(pv_sans),
                rank=rank,
            )
        )
    return candidates


def _build_complexity(
    legal: list[chess.Move],
    candidates: list[CandidateMove],
) -> ComplexityScore:
    branching = float(len(legal))

    # eval spread across top candidates → volatility
    evals = [c.eval_cp for c in candidates if c.eval_cp is not None]
    if len(evals) >= 2:
        volatility = min(1.0, statistics.stdev(evals) / 100.0)
    else:
        volatility = 0.0

    # fraction of PV first-moves that are captures (proxy for tactics)
    tactical = 0.0

    move_ambiguity = 1.0 / max(1, len(legal))

    # composite: average of branching (normalized to 40), volatility, 1-ambiguity
    composite = min(
        1.0,
        (branching / 40.0 + volatility + (1.0 - move_ambiguity)) / 3.0,
    )

    return ComplexityScore(
        branching_factor=branching,
        eval_volatility=volatility,
        tactical_density=tactical,
        move_ambiguity=move_ambiguity,
        composite=composite,
    )


def _terminal_position(board: chess.Board, ply: int, side: PlayerColor) -> Position:
    complexity = ComplexityScore(
        branching_factor=0.0,
        eval_volatility=0.0,
        tactical_density=0.0,
        move_ambiguity=1.0,
        composite=0.0,
    )
    return Position(
        ply=ply,
        fen=board.fen(),
        side_to_move=side,
        eval_cp=None,
        mate_in=None,
        top_moves=(),
        complexity=complexity,
        is_critical=True,
        is_only_move=True,
        is_book=False,
    )
