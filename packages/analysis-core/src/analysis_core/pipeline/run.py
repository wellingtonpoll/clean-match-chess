"""AuditRun orchestrator for single-game audits (T057).

Wires:
  PGN load → Analyzer per position → Segmentation → Signals →
  Aggregate score → AuditRun persisted to disk.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import chess
import chess.engine

# Heuristics
from heuristics.behavioral_patterns import blunder_suppression, precision_burst
from heuristics.complexity_analysis import complexity_score
from heuristics.engine_correlation import engine_correlation
from heuristics.regime_shift import regime_shift_score
from heuristics.scoring import aggregate_score
from heuristics.scoring.account_profile import build_account_profile
from heuristics.tactical_detection import tactical_density
from heuristics.timing_analysis import timing_anomaly
from shared_types.audit_run import (
    AuditRun,
    EngineFingerprint,
    RunMode,
    RunStatus,
)
from shared_types.game import Game, PlayerColor, PlayerRef, Position
from shared_types.score import SuspicionScore
from shared_types.signal import HeuristicVersion, SignalAggregate

from analysis_core.engine.analysis import Analyzer, EngineAnalyzer, StaticAnalyzer
from analysis_core.manifest import build_manifest
from analysis_core.pipeline.cache import cleanmatch_home, persist_manifest
from analysis_core.pipeline.segmentation import segment_game

DEFAULT_OPENING_BOOK_SHA256 = "0" * 64
DEFAULT_DESIGN_SYSTEM_VERSION = "0.1.0"


def run_single_game(
    game: Game,
    *,
    subject: PlayerColor = PlayerColor.WHITE,
    analyzer: Analyzer | None = None,
    engine: EngineFingerprint | None = None,
    engine_path: str | None = None,
    engine_image: str | None = None,
    heuristics: tuple[HeuristicVersion, ...] | None = None,
    design_system_version: str = DEFAULT_DESIGN_SYSTEM_VERSION,
    opening_book_sha256: str = DEFAULT_OPENING_BOOK_SHA256,
    persist_root: Path | None = None,
) -> AuditRun:
    engine_command = _resolve_engine_command(engine_path, engine_image)
    if analyzer is None and engine_command:
        with EngineAnalyzer(engine_command) as ea:
            engine = engine or (
                engine_fingerprint_from_path(engine_path) if engine_path
                else _default_engine_fp()
            )
            heuristics = heuristics or _default_heuristics()
            positions = _analyse_positions(game, ea)
            return _build_run(
                game, positions, subject=subject,
                engine=engine, heuristics=heuristics,
                design_system_version=design_system_version,
                opening_book_sha256=opening_book_sha256,
                persist_root=persist_root,
            )
    analyzer = analyzer or StaticAnalyzer()
    engine = engine or _default_engine_fp()
    heuristics = heuristics or _default_heuristics()
    positions = _analyse_positions(game, analyzer)
    return _build_run(
        game, positions, subject=subject,
        engine=engine, heuristics=heuristics,
        design_system_version=design_system_version,
        opening_book_sha256=opening_book_sha256,
        persist_root=persist_root,
    )


def run_username_batch(
    username: str,
    games: tuple[Game, ...],
    *,
    subject: PlayerColor = PlayerColor.WHITE,
    analyzer: Analyzer | None = None,
    engine: EngineFingerprint | None = None,
    engine_path: str | None = None,
    engine_image: str | None = None,
    heuristics_set: tuple[HeuristicVersion, ...] | None = None,
    design_system_version: str = DEFAULT_DESIGN_SYSTEM_VERSION,
    opening_book_sha256: str = DEFAULT_OPENING_BOOK_SHA256,
    platform: str = "chesscom",
) -> AuditRun:
    """Audit a batch of games for one username. Builds AccountProfile."""
    engine_command = _resolve_engine_command(engine_path, engine_image)
    # Open one engine process for the entire batch.
    if analyzer is None and engine_command:
        resolved_engine = engine or (
            engine_fingerprint_from_path(engine_path) if engine_path
            else _default_engine_fp()
        )
        resolved_heuristics = heuristics_set or _default_heuristics()
        with EngineAnalyzer(engine_command) as ea:
            per_game_runs = [
                run_single_game(
                    game,
                    subject=subject,
                    analyzer=ea,
                    engine=resolved_engine,
                    heuristics=resolved_heuristics,
                    design_system_version=design_system_version,
                    opening_book_sha256=opening_book_sha256,
                )
                for game in games
            ]
    else:
        per_game_runs = [
            run_single_game(
                game,
                subject=subject,
                analyzer=analyzer,
                engine=engine,
                heuristics=heuristics_set,
                design_system_version=design_system_version,
                opening_book_sha256=opening_book_sha256,
            )
            for game in games
        ]

    per_game_scores = tuple(r.score for r in per_game_runs if r.score is not None)
    run_ids = tuple(r.id for r in per_game_runs)
    profile = build_account_profile(
        username,
        per_game_scores,
        platform=platform,
        run_ids=run_ids,
    )

    subject_ref = PlayerRef(color=subject, username=username, subject=True)
    return AuditRun(
        id=uuid.uuid4().hex,
        created_at=datetime.now(UTC),
        mode=RunMode.USERNAME_BATCH,
        subject=subject_ref,
        games=run_ids,
        engine=engine or _default_engine_fp(),
        heuristic_set=heuristics_set or _default_heuristics(),
        score=None,
        account_profile=profile,
        status=RunStatus.COMPLETE,
    )


def _resolve_engine_command(
    engine_path: str | None,
    engine_image: str | None,
) -> str | list[str] | None:
    if engine_path:
        return engine_path
    if engine_image:
        return ["podman", "run", "--rm", "-i", engine_image]
    return None


def engine_fingerprint_from_path(binary_path: str) -> EngineFingerprint:
    """Open Stockfish briefly to read its version, then compute binary SHA256."""
    path = Path(binary_path)
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    with chess.engine.SimpleEngine.popen_uci(binary_path) as eng:
        name = eng.id.get("name", "Stockfish")
        version = name.split(" ")[-1] if " " in name else "unknown"
    return EngineFingerprint(
        name="Stockfish",
        version=version,
        binary_sha256=sha256,
        uci_options={"Threads": 1, "Hash": 256, "MultiPV": 5, "UseNNUE": True},
    )


def _build_run(
    game: Game,
    positions: tuple[Position, ...],
    *,
    subject: PlayerColor,
    engine: EngineFingerprint,
    heuristics: tuple[HeuristicVersion, ...],
    design_system_version: str,
    opening_book_sha256: str,
    persist_root: Path | None,
) -> AuditRun:
    segments = segment_game(positions)

    signals: list[SignalAggregate] = []
    signals.append(complexity_score(positions))
    signals.append(tactical_density(positions))
    signals.append(regime_shift_score(segments))
    top1, top3, weighted = engine_correlation(positions, game.moves)
    signals.extend([top1, top3, weighted])
    signals.append(precision_burst(positions, game.moves))
    signals.append(blunder_suppression(positions))
    signals.append(timing_anomaly(positions, game.moves))

    score = aggregate_score(tuple(signals))
    subject_player = _resolve_subject(game.players, subject)

    manifest = build_manifest(
        engine=engine,
        heuristics=heuristics,
        input_pgn_sha256=game.pgn_sha256,
        opening_book_sha256=opening_book_sha256,
        design_system_version=design_system_version,
    )

    run = AuditRun(
        id=uuid.uuid4().hex,
        created_at=datetime.now(UTC),
        mode=RunMode.SINGLE_GAME,
        subject=subject_player,
        games=(game.id,),
        engine=engine,
        heuristic_set=heuristics,
        score=score,
        status=RunStatus.COMPLETE,
    )

    root = persist_root or cleanmatch_home()
    _persist(run, manifest, score, root, game=game, positions=positions)
    persist_manifest(manifest)
    return run


def _analyse_positions(game: Game, analyzer: Analyzer) -> tuple[Position, ...]:
    board = chess.Board()
    positions: list[Position] = []
    positions.append(analyzer.analyse(board, ply=0))
    for ply, move in enumerate(game.moves, start=1):
        chess_move = chess.Move.from_uci(move.uci)
        if chess_move not in board.legal_moves:
            break
        board.push(chess_move)
        positions.append(analyzer.analyse(board, ply=ply))
    return tuple(positions)


def _resolve_subject(players: tuple[PlayerRef, PlayerRef], target: PlayerColor) -> PlayerRef:
    for p in players:
        if p.color is target:
            return p
    return players[0]


def _default_engine_fp() -> EngineFingerprint:
    return EngineFingerprint(
        name="Stockfish",
        version="0.0.0-static",
        binary_sha256="0" * 64,
        uci_options={"Threads": 1, "Hash": 256, "MultiPV": 5, "UseNNUE": True},
    )


def _default_heuristics() -> tuple[HeuristicVersion, ...]:
    return (
        HeuristicVersion(
            name="engine-correlation",
            version="0.1.0",
            git_sha="0000000",
            owner="cleanmatch",
            changelog_path="packages/heuristics/CHANGELOG.md",
        ),
        HeuristicVersion(
            name="complexity-analysis",
            version="0.1.0",
            git_sha="0000000",
            owner="cleanmatch",
            changelog_path="packages/heuristics/CHANGELOG.md",
        ),
        HeuristicVersion(
            name="tactical-detection",
            version="0.1.0",
            git_sha="0000000",
            owner="cleanmatch",
            changelog_path="packages/heuristics/CHANGELOG.md",
        ),
        HeuristicVersion(
            name="regime-shift",
            version="0.1.0",
            git_sha="0000000",
            owner="cleanmatch",
            changelog_path="packages/heuristics/CHANGELOG.md",
        ),
        HeuristicVersion(
            name="behavioral-patterns",
            version="0.1.0",
            git_sha="0000000",
            owner="cleanmatch",
            changelog_path="packages/heuristics/CHANGELOG.md",
        ),
        HeuristicVersion(
            name="timing-analysis",
            version="0.1.0",
            git_sha="0000000",
            owner="cleanmatch",
            changelog_path="packages/heuristics/CHANGELOG.md",
        ),
    )


def _persist(
    run: AuditRun,
    manifest: object,
    score: SuspicionScore,
    root: Path,
    *,
    game: Game,
    positions: tuple[Position, ...],
) -> Path:
    dest = root / "runs" / run.id
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), sort_keys=True, default=str)  # type: ignore[attr-defined]
    )
    (dest / "run.json").write_text(
        json.dumps(run.model_dump(mode="json"), sort_keys=True, default=str)
    )
    (dest / "score.json").write_text(
        json.dumps(score.model_dump(mode="json"), sort_keys=True, default=str)
    )
    (dest / "game.json").write_text(
        json.dumps(game.model_dump(mode="json"), sort_keys=True, default=str)
    )
    (dest / "positions.json").write_text(
        json.dumps(
            [p.model_dump(mode="json") for p in positions],
            sort_keys=True,
            default=str,
        )
    )
    return dest
