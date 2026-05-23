"""Timeline renderer (T070)."""

from __future__ import annotations

from datetime import UTC, datetime

import chess
import pytest
from analysis_core.engine.analysis import StaticAnalyzer
from analysis_core.ingest.pgn_loader import load_pgn_text
from cleanmatch_cli.output.timeline_renderer import render_timeline
from shared_types.audit_run import AuditRun, EngineFingerprint, RunMode, RunStatus
from shared_types.game import PlayerColor, PlayerRef
from shared_types.score import RiskLevel, SuspicionScore
from shared_types.signal import HeuristicVersion


@pytest.fixture
def small_game():
    pgn = (
        '[Event "?"]\n[White "alice"]\n[Black "bob"]\n[Result "1-0"]\n'
        '[TimeControl "600"]\n\n'
        "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 1-0\n"
    )
    return load_pgn_text(pgn)


def _stub_run() -> AuditRun:
    return AuditRun(
        id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        created_at=datetime.now(UTC),
        mode=RunMode.SINGLE_GAME,
        subject=PlayerRef(color=PlayerColor.WHITE, username="alice", subject=True),
        engine=EngineFingerprint(
            name="Stockfish",
            version="static",
            binary_sha256="0" * 64,
            uci_options={"Threads": 1, "MultiPV": 5},
        ),
        heuristic_set=(
            HeuristicVersion(
                name="engine-correlation",
                version="0.1.0",
                git_sha="0000000",
                owner="cleanmatch",
                changelog_path="x",
            ),
        ),
        status=RunStatus.COMPLETE,
        score=_stub_score(),
    )


def _stub_score() -> SuspicionScore:
    return SuspicionScore(score=0.1, risk_level=RiskLevel.LOW, confidence_interval=(0.05, 0.2))


def test_timeline_emits_one_header_and_one_line_per_move(small_game) -> None:
    a = StaticAnalyzer()
    positions = tuple(a.analyse(b, ply=i) for i, b in enumerate(_boards(small_game)))
    out = render_timeline(_stub_run(), small_game, positions, _stub_score())
    assert any("ply" in line for line in out[:5])
    move_lines = [line for line in out if line.strip() and line.lstrip()[0].isdigit()]
    assert len(move_lines) == len(small_game.moves)


def test_timeline_renders_risk_and_dominant_signals(small_game) -> None:
    a = StaticAnalyzer()
    positions = tuple(a.analyse(b, ply=i) for i, b in enumerate(_boards(small_game)))
    score = SuspicionScore(
        score=0.42,
        risk_level=RiskLevel.MEDIUM,
        confidence_interval=(0.3, 0.5),
        dominant_signals=("engine-correlation/weighted",),
    )
    out = render_timeline(_stub_run(), small_game, positions, score)
    joined = "\n".join(out)
    assert "MEDIUM" in joined
    assert "engine-correlation/weighted" in joined


def _boards(game) -> list:
    out = [chess.Board()]
    b = chess.Board()
    for m in game.moves:
        mv = chess.Move.from_uci(m.uci)
        if mv in b.legal_moves:
            b.push(mv)
            out.append(b.copy())
    return out
