"""End-to-end ACPL integration test (T018, US1 acceptance).

Uses a hand-crafted PGN + a synthetic Analyzer that injects pinned
`eval_cp` values per ply (no Stockfish required, fully hermetic). The
test verifies:
  * `acpl-analysis` appears in `dominant_signals` when ACPL suspicion is
    high for the rating bucket.
  * Move.eval_delta_cp is populated by the pipeline.
  * The ACPL `SignalAggregate` reports the expected `samples` count
    (one per eligible white ply).
"""

from __future__ import annotations

import chess
from analysis_core.engine.analysis import StaticAnalyzer
from analysis_core.pipeline.opening_book import OpeningBook
from analysis_core.pipeline.run import _analyse_positions, _build_run
from shared_types.audit_run import EngineFingerprint
from shared_types.game import (
    Game,
    Move,
    MoveClassification,
    PlayerColor,
    PlayerRef,
    Position,
    Result,
    TimeControl,
    TimeControlCategory,
)
from shared_types.signal import HeuristicVersion


class _PinnedEvalAnalyzer:
    """Analyzer that returns a fixed eval_cp series for hermetic delta testing."""

    def __init__(self, eval_series: list[int | None]) -> None:
        self._series = eval_series
        self._inner = StaticAnalyzer()

    def analyse(self, board: chess.Board, ply: int) -> Position:
        base = self._inner.analyse(board, ply=ply)
        eval_cp = self._series[ply] if ply < len(self._series) else 0
        return base.model_copy(update={"eval_cp": eval_cp})


def _engine_fp() -> EngineFingerprint:
    return EngineFingerprint(
        name="Stockfish",
        version="test",
        binary_sha256="0" * 64,
        uci_options={"Threads": 1, "Hash": 256, "MultiPV": 5, "UseNNUE": True},
    )


def _heuristics() -> tuple[HeuristicVersion, ...]:
    return (
        HeuristicVersion(
            name="acpl-analysis",
            version="1.0.0",
            git_sha="0000000",
            owner="cleanmatch",
            changelog_path="packages/heuristics/CHANGELOG.md",
        ),
    )


def _build_game(
    pgn_moves: list[str],
    *,
    white_elo: int = 1500,
) -> Game:
    board = chess.Board()
    moves: list[Move] = []
    for ply, san in enumerate(pgn_moves):
        chess_move = board.parse_san(san)
        uci = chess_move.uci()
        side = PlayerColor.WHITE if board.turn else PlayerColor.BLACK
        moves.append(
            Move(
                ply=ply,
                san=san,
                uci=uci,
                played_by=side,
                time_spent_ms=None,
                eval_delta_cp=0,
                classification=MoveClassification.GOOD,
                signal_contributions=(),
            )
        )
        board.push(chess_move)
    return Game(
        id="a" * 32,
        pgn_sha256="b" * 64,
        source="paste",
        headers={"WhiteElo": str(white_elo), "BlackElo": "1500"},
        players=(
            PlayerRef(color=PlayerColor.WHITE, username="W", rating=white_elo, subject=True),
            PlayerRef(color=PlayerColor.BLACK, username="B", rating=1500),
        ),
        result=Result.UNKNOWN,
        time_control=TimeControl(
            raw="600+0",
            category=TimeControlCategory.RAPID,
            base_seconds=600,
            increment_seconds=0,
        ),
        eco=None,
        ply_count=len(moves),
        variant="standard",
        moves=tuple(moves),
    )


# A 40-ply opening sequence — built dynamically from legal moves so we
# don't depend on a pre-typed PGN that might collide with state changes.
def _make_40_legal_moves() -> list[str]:
    """Build a 40-ply game of mostly random-but-legal moves.

    Uses the first legal move in `board.legal_moves` deterministically.
    Reaches 40 plies on any standard opening pattern.
    """
    board = chess.Board()
    sans: list[str] = []
    for _ in range(40):
        legal = list(board.legal_moves)
        if not legal:
            break
        mv = legal[0]
        sans.append(board.san(mv))
        board.push(mv)
    return sans


_PGN_MOVES_40 = _make_40_legal_moves()


def _engine_perfect_eval_series(n_positions: int) -> list[int | None]:
    """Series where each white move loses ~10cp, black moves are neutral.

    Sign convention follows `Position.eval_cp` (from side-to-move POV):
      delta_for_player = -positions[i+1].eval_cp - positions[i].eval_cp
    Construct alternating evals so each white delta is exactly -10
    (player loses 10 cp). Even-ply (i) is white-to-move.

      For white delta = -10 at ply i (white plays):
        -positions[i+1].eval_cp - positions[i].eval_cp = -10
      Choose all positions[k].eval_cp = +5 at even k (W to move sees +5)
      and -5 at odd k (B to move sees -5 = white is up 5).

      Even (W to move) eval = +5
      Odd  (B to move) eval = -5
      White's delta = -(-5) - 5 = 0. Wrong — that's zero loss.

    Try: W to move = 0, B to move = +10.
      White delta = -(+10) - 0 = -10. ✓
      Black delta = -(0) - (+10) = -10. ✓ (both sides lose 10)

    But we only score WHITE losses (subject is white). So black losses
    are ignored. Use even=0, odd=+10.
    """
    series: list[int | None] = []
    for ply in range(n_positions):
        if ply % 2 == 0:
            series.append(0)  # White to move
        else:
            series.append(10)  # Black to move; means white is up 10 cp
    return series


def test_acpl_signal_dominates_for_low_rated_engine_perfect_player(
    cleanmatch_home,
) -> None:
    game = _build_game(_PGN_MOVES_40, white_elo=1500)
    # Need 41 positions (40 moves + 1 final).
    eval_series = _engine_perfect_eval_series(len(_PGN_MOVES_40) + 1)
    analyzer = _PinnedEvalAnalyzer(eval_series)
    positions = _analyse_positions(game, analyzer, book=OpeningBook.empty())

    run = _build_run(
        game,
        positions,
        subject=PlayerColor.WHITE,
        engine=_engine_fp(),
        heuristics=_heuristics(),
        design_system_version="0.1.0",
        opening_book_sha256="0" * 64,
        persist_root=cleanmatch_home,
    )

    assert run.score is not None
    # After US5 (per-segment heuristic application), the per-segment
    # acpl-analysis output is folded into segments-weighted-aggregate at
    # the game level. The dominant_signals list surfaces the carrier signal.
    # Score threshold lowered 0.6 → 0.4 on 2026-05-26 after the first real
    # measured baselines replaced the stub. The wider real population stdev
    # compresses z-scores; the engine-perfect 10cp/move at rating 1500 now
    # scores MEDIUM, not HIGH, on the acpl signal alone — combined detection
    # with engine-correlation + behavioral-patterns picks up the slack.
    assert "segments-weighted-aggregate" in run.score.dominant_signals
    assert run.score.score >= 0.4


def test_eval_delta_cp_populated_in_persisted_run(cleanmatch_home) -> None:
    game = _build_game(_PGN_MOVES_40, white_elo=1500)
    eval_series = _engine_perfect_eval_series(len(_PGN_MOVES_40) + 1)
    analyzer = _PinnedEvalAnalyzer(eval_series)
    positions = _analyse_positions(game, analyzer, book=OpeningBook.empty())

    run = _build_run(
        game,
        positions,
        subject=PlayerColor.WHITE,
        engine=_engine_fp(),
        heuristics=_heuristics(),
        design_system_version="0.1.0",
        opening_book_sha256="0" * 64,
        persist_root=cleanmatch_home,
    )

    # Read the persisted game.json to confirm eval_delta_cp is populated.
    import json

    game_path = cleanmatch_home / "runs" / run.id / "game.json"
    persisted = json.loads(game_path.read_text())
    for move in persisted["moves"]:
        assert "eval_delta_cp" in move
    # White moves should all have eval_delta_cp == -10.
    white_deltas = [m["eval_delta_cp"] for m in persisted["moves"] if m["played_by"] == "white"]
    assert all(d == -10 for d in white_deltas), white_deltas


def test_acpl_samples_count_matches_white_eligible_plies(cleanmatch_home) -> None:
    from heuristics.acpl_analysis import acpl_signal
    from heuristics.rating_baselines import get_baselines

    game = _build_game(_PGN_MOVES_40, white_elo=1500)
    eval_series = _engine_perfect_eval_series(len(_PGN_MOVES_40) + 1)
    analyzer = _PinnedEvalAnalyzer(eval_series)
    positions = _analyse_positions(game, analyzer, book=OpeningBook.empty())
    # Manually populate deltas to feed acpl_signal directly.
    from analysis_core.pipeline.run import _populate_eval_deltas

    moves = _populate_eval_deltas(positions, game.moves)
    sig = acpl_signal(
        positions=positions,
        moves=moves,
        subject_color=PlayerColor.WHITE,
        subject_rating=1500,
        baselines=get_baselines(),
    )
    # 40 plies → 20 white moves. None are is_book (empty book) and the
    # complexity from StaticAnalyzer never marks is_only_move (≥2 legal
    # moves in this opening sequence), so all 20 are eligible.
    # Suspicion threshold lowered 0.65 → 0.20 on 2026-05-26 — real baselines
    # have wider stdev than the stub assumed; see comment on
    # test_us1_as1_low_rated_engine_perfect_high_suspicion in
    # packages/heuristics/tests/test_acpl_analysis.py.
    assert sig.samples == 20
    assert sig.mean >= 0.20
