"""Integration test — pipeline attaches manifest in-band to AuditRun (feature 005 T027).

Uses the same hermetic StaticAnalyzer pattern as ``test_run_acpl_integration``
to avoid Stockfish. Asserts the returned ``AuditRun`` carries a non-None
``manifest`` whose ``rating_baselines_sha256`` and ``signal_versions``
reflect the bundled artifacts (not their ``"0" * 64`` / empty-dict defaults).
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
    Result,
    TimeControl,
    TimeControlCategory,
)
from shared_types.signal import HeuristicVersion


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


def _short_game() -> Game:
    board = chess.Board()
    moves: list[Move] = []
    sans = [
        "e4",
        "e5",
        "Nf3",
        "Nc6",
        "Bb5",
        "a6",
        "Ba4",
        "Nf6",
        "O-O",
        "Be7",
        "Re1",
        "b5",
        "Bb3",
        "d6",
        "c3",
        "O-O",
        "h3",
        "Nb8",
        "d4",
        "Nbd7",
    ]
    for ply, san in enumerate(sans):
        chess_move = board.parse_san(san)
        side = PlayerColor.WHITE if board.turn else PlayerColor.BLACK
        moves.append(
            Move(
                ply=ply,
                san=san,
                uci=chess_move.uci(),
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
        headers={"WhiteElo": "1500", "BlackElo": "1500"},
        players=(
            PlayerRef(color=PlayerColor.WHITE, username="W", rating=1500, subject=True),
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


def test_audit_run_manifest_populated_in_band(cleanmatch_home) -> None:  # type: ignore[no-untyped-def]
    game = _short_game()
    analyzer = StaticAnalyzer()
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

    assert run.manifest is not None, "feature 005 FR-003: manifest must be in-band on AuditRun"
    assert len(run.manifest.rating_baselines_sha256) == 64
    assert run.manifest.rating_baselines_sha256 != "0" * 64, (
        "rating_baselines_sha256 should reflect the bundled artifact, not the default"
    )
    assert run.manifest.signal_versions, "signal_versions dict must be populated"
    assert "acpl-analysis" in run.manifest.signal_versions


def test_audit_run_manifest_round_trips_via_json(cleanmatch_home) -> None:  # type: ignore[no-untyped-def]
    game = _short_game()
    analyzer = StaticAnalyzer()
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

    serialized = run.model_dump_json()
    from shared_types.audit_run import AuditRun

    restored = AuditRun.model_validate_json(serialized)
    assert restored.manifest is not None
    assert (
        restored.manifest.rating_baselines_sha256 == run.manifest.rating_baselines_sha256  # type: ignore[union-attr]
    )
    assert restored.manifest.signal_versions == run.manifest.signal_versions  # type: ignore[union-attr]
