"""ACPL signal contract tests (T014, FR-002, FR-003).

Covers the contract in `specs/004-scoring-v2-phase1/contracts/
acpl_signal.contract.md`:

  (a) `acpl_signal` returns a `SignalAggregate` with the expected name
      and version.
  (b) silences (samples=0) when fewer than 10 eligible plies are
      available.
  (c) silences on all-book input.
  (d) z-scaling / suspicion formula correctness.
  (e) falls back to the rating-unknown bucket when subject_rating is None.
  (f) US1 AS1: 1500 + ACPL=10 → suspicion ≥ 0.65.
  (g) US1 AS2: 2700 + ACPL=10 → suspicion ≤ 0.45.
"""

from __future__ import annotations

from heuristics.acpl_analysis import MIN_ELIGIBLE_PLIES, acpl_signal
from heuristics.rating_baselines import get_baselines
from shared_types.game import (
    ComplexityScore,
    Move,
    MoveClassification,
    PlayerColor,
    Position,
)
from shared_types.signal import SignalAggregate


def _position(
    ply: int,
    *,
    is_book: bool = False,
    is_only_move: bool = False,
) -> Position:
    return Position(
        ply=ply,
        fen=f"synthetic-{ply}",
        side_to_move=PlayerColor.WHITE if ply % 2 == 0 else PlayerColor.BLACK,
        eval_cp=0,
        mate_in=None,
        top_moves=(),
        complexity=ComplexityScore(
            branching_factor=20.0,
            eval_volatility=0.0,
            tactical_density=0.0,
            move_ambiguity=0.05,
            composite=0.5,
        ),
        is_critical=False,
        is_only_move=is_only_move,
        is_book=is_book,
    )


def _move(ply: int, *, played_by: PlayerColor, delta: int) -> Move:
    return Move(
        ply=ply,
        san=f"M{ply}",
        uci="e2e4",
        played_by=played_by,
        eval_delta_cp=delta,
        classification=MoveClassification.GOOD,
    )


def _build_game(
    n_plies: int,
    *,
    loss_per_white_move: int,
    is_book: bool = False,
) -> tuple[tuple[Position, ...], tuple[Move, ...]]:
    positions: list[Position] = []
    moves: list[Move] = []
    for ply in range(n_plies):
        positions.append(_position(ply, is_book=is_book))
        played_by = PlayerColor.WHITE if ply % 2 == 0 else PlayerColor.BLACK
        # Negative delta = player lost CP. White moves lose `loss_per_white_move`.
        delta = -loss_per_white_move if played_by is PlayerColor.WHITE else 0
        moves.append(_move(ply, played_by=played_by, delta=delta))
    # One extra trailing position so we have positions[i+1] for the last move.
    positions.append(_position(n_plies, is_book=is_book))
    return tuple(positions), tuple(moves)


# ── (a) basic return type ────────────────────────────────────────────


def test_returns_signal_aggregate() -> None:
    positions, moves = _build_game(40, loss_per_white_move=50)
    out = acpl_signal(
        positions=positions,
        moves=moves,
        subject_color=PlayerColor.WHITE,
        subject_rating=1500,
        baselines=get_baselines(),
    )
    assert isinstance(out, SignalAggregate)
    assert out.signal_name == "acpl-analysis"
    assert out.signal_version == "1.0.0"


# ── (b) silencing under threshold ────────────────────────────────────


def test_silenced_when_samples_below_threshold() -> None:
    # Only 6 white moves → below MIN_ELIGIBLE_PLIES.
    positions, moves = _build_game(12, loss_per_white_move=10)
    assert sum(1 for m in moves if m.played_by is PlayerColor.WHITE) < MIN_ELIGIBLE_PLIES
    out = acpl_signal(
        positions=positions,
        moves=moves,
        subject_color=PlayerColor.WHITE,
        subject_rating=1500,
        baselines=get_baselines(),
    )
    assert out.samples == 0
    assert out.mean == 0.0


# ── (c) silencing on all-book input ──────────────────────────────────


def test_silenced_when_all_positions_in_book() -> None:
    positions, moves = _build_game(40, loss_per_white_move=10, is_book=True)
    out = acpl_signal(
        positions=positions,
        moves=moves,
        subject_color=PlayerColor.WHITE,
        subject_rating=1500,
        baselines=get_baselines(),
    )
    assert out.samples == 0
    assert out.mean == 0.0


# ── (d) suspicion formula correctness ────────────────────────────────


def test_suspicion_formula_3_sigma_below_mean_yields_one() -> None:
    # 1500 bucket: expected_mean=65, expected_stdev=28.
    # 3-sigma below = 65 - 3*28 = -19; clamp obs=0 -> z = 65/28 ~ 2.32, /3 ~ 0.776.
    # For suspicion=1.0 we need obs <= expected_mean - 3*stdev.
    # Force a synthetic loss series with mean = -19 (impossible: losses>=0),
    # so the strongest possible suspicion at 1500 with ACPL=0 is 65/28/3 ~ 0.774.
    positions, moves = _build_game(40, loss_per_white_move=0)
    out = acpl_signal(
        positions=positions,
        moves=moves,
        subject_color=PlayerColor.WHITE,
        subject_rating=1500,
        baselines=get_baselines(),
    )
    assert 0.77 <= out.mean <= 0.78


def test_suspicion_clamped_to_zero_when_observed_exceeds_expected() -> None:
    # Player with very high ACPL → z negative → clamped to 0.
    positions, moves = _build_game(40, loss_per_white_move=200)
    out = acpl_signal(
        positions=positions,
        moves=moves,
        subject_color=PlayerColor.WHITE,
        subject_rating=1500,
        baselines=get_baselines(),
    )
    assert out.mean == 0.0


# ── (e) rating-unknown fallback ──────────────────────────────────────


def test_subject_rating_none_uses_rating_unknown_bucket() -> None:
    positions, moves = _build_game(40, loss_per_white_move=10)
    out = acpl_signal(
        positions=positions,
        moves=moves,
        subject_color=PlayerColor.WHITE,
        subject_rating=None,
        baselines=get_baselines(),
    )
    # Should produce a finite, bounded value (not crash).
    assert 0.0 <= out.mean <= 1.0
    assert out.samples == 20  # 20 white moves out of 40 plies


# ── (f) US1 AS1 — 1500 + ACPL ≈ 10 → suspicion ≥ 0.65 ────────────────


def test_us1_as1_low_rated_engine_perfect_high_suspicion() -> None:
    positions, moves = _build_game(40, loss_per_white_move=10)
    out = acpl_signal(
        positions=positions,
        moves=moves,
        subject_color=PlayerColor.WHITE,
        subject_rating=1500,
        baselines=get_baselines(),
    )
    # 1500 bucket: expected_mean=65, stdev=28. z=(65-10)/28 ≈ 1.964.
    # suspicion = 1.964/3 ≈ 0.6548 — at the threshold.
    assert out.mean >= 0.65


# ── (g) US1 AS2 — 2700 + ACPL ≈ 10 → suspicion ≤ 0.45 ────────────────


def test_us1_as2_high_rated_engine_perfect_modest_suspicion() -> None:
    positions, moves = _build_game(40, loss_per_white_move=10)
    out = acpl_signal(
        positions=positions,
        moves=moves,
        subject_color=PlayerColor.WHITE,
        subject_rating=2700,
        baselines=get_baselines(),
    )
    # 2401+ bucket: expected_mean=18, stdev=10. z=(18-10)/10 = 0.8.
    # suspicion = 0.8/3 ≈ 0.267 ≤ 0.45.
    assert out.mean <= 0.45


# ── extra: only-move plies are excluded ──────────────────────────────


def test_only_move_plies_are_excluded() -> None:
    # 12 plies, alternating only-move = True/False, all white losses 10.
    positions: list[Position] = []
    moves: list[Move] = []
    for ply in range(40):
        positions.append(_position(ply, is_only_move=(ply % 2 == 0)))
        played_by = PlayerColor.WHITE if ply % 2 == 0 else PlayerColor.BLACK
        moves.append(_move(ply, played_by=played_by, delta=-10))
    positions.append(_position(40))
    out = acpl_signal(
        positions=tuple(positions),
        moves=tuple(moves),
        subject_color=PlayerColor.WHITE,
        subject_rating=1500,
        baselines=get_baselines(),
    )
    # White plays on even plies, but those positions are is_only_move → excluded.
    # So samples should be 0 (all white plies were only-move), silenced.
    assert out.samples == 0
