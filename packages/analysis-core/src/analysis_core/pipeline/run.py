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
from heuristics.acpl_analysis import acpl_signal
from heuristics.behavioral_patterns import blunder_suppression, precision_burst
from heuristics.complexity_analysis import complexity_score
from heuristics.engine_correlation import engine_correlation
from heuristics.rating_baselines import BASELINES_PATH, get_baselines
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
from shared_types.game import Game, Move, PlayerColor, PlayerRef, Position
from shared_types.score import SuspicionScore
from shared_types.signal import HeuristicVersion, SignalAggregate

from analysis_core.engine.analysis import Analyzer, EngineAnalyzer, StaticAnalyzer
from analysis_core.manifest import build_manifest
from analysis_core.pipeline.cache import cleanmatch_home, persist_manifest
from analysis_core.pipeline.opening_book import OpeningBook
from analysis_core.pipeline.segmentation import segment_game

DEFAULT_OPENING_BOOK_SHA256 = "0" * 64
DEFAULT_DESIGN_SYSTEM_VERSION = "0.1.0"

# Sentinel value: pass this to opt out of opening-book lookup.
NO_BOOK_SENTINEL = ""

# Per-signal version strings stamped into the manifest (FR-012, T010).
SIGNAL_VERSIONS: dict[str, str] = {
    "acpl-analysis": "1.0.0",
    "engine-correlation": "0.1.0",
    "complexity-analysis": "0.1.0",
    "tactical-detection": "0.1.0",
    "regime-shift": "0.1.0",
    "behavioral-patterns": "0.1.0",
    "timing-analysis": "0.1.0",
}


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
    moves = _populate_eval_deltas(positions, game.moves)
    game = _game_with_moves(game, moves)
    segments = segment_game(positions)

    subject_rating = _extract_subject_rating(game, subject)
    baselines = get_baselines()

    signals: list[SignalAggregate] = []
    signals.append(complexity_score(positions))
    signals.append(tactical_density(positions))
    signals.append(regime_shift_score(segments))
    top1, top3, weighted = engine_correlation(positions, moves)
    signals.extend([top1, top3, weighted])
    signals.append(precision_burst(positions, moves))
    signals.append(blunder_suppression(positions))
    signals.append(timing_anomaly(positions, moves))
    signals.append(
        acpl_signal(
            positions=positions,
            moves=moves,
            subject_color=subject,
            subject_rating=subject_rating,
            baselines=baselines,
        )
    )

    score = aggregate_score(tuple(signals))
    subject_player = _resolve_subject(game.players, subject)

    # T010: stamp opening-book + rating-baselines provenance into the manifest.
    # `ReproducibilityManifest` already carries `opening_book_sha256`. The
    # rating-baselines sha256 and per-signal versions are computed here so
    # downstream consumers (audit JSON exports, debugging) can inspect them
    # even though the strict shared-types schema does not yet expose
    # dedicated fields for them.
    rating_baselines_sha256 = _hash_rating_baselines()
    signal_versions = dict(SIGNAL_VERSIONS)
    # Surfaced via persisted artifacts in a follow-up (schema-bound).
    _ = (rating_baselines_sha256, signal_versions)

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


def _populate_eval_deltas(
    positions: tuple[Position, ...],
    moves: tuple[Move, ...],
) -> tuple[Move, ...]:
    """Return `moves` with `eval_delta_cp` filled per FR-001.

    Sign convention: positive means the played move improved the player's
    position. `Position.eval_cp` is from the side-to-move perspective at
    that position, so for move `i` played from positions[i]:

        delta = (-positions[i+1].eval_cp) - positions[i].eval_cp

    (the unary minus flips the post-move eval from the opponent's
    perspective back to the player's perspective).

    When either eval is missing, delta is 0 (the schema requires an int;
    see FR-001 / US1 AS3 — "or 0 if no eval was available").
    """
    out: list[Move] = []
    for idx, mv in enumerate(moves):
        if idx + 1 >= len(positions):
            out.append(mv)
            continue
        before = positions[idx].eval_cp
        after = positions[idx + 1].eval_cp
        if before is None or after is None:
            delta = 0
        else:
            delta = (-after) - before
        if mv.eval_delta_cp == delta:
            out.append(mv)
        else:
            out.append(mv.model_copy(update={"eval_delta_cp": delta}))
    return tuple(out)


def _game_with_moves(game: Game, moves: tuple[Move, ...]) -> Game:
    """Return `game` with `moves` swapped in. Cheap immutable update."""
    if game.moves is moves:
        return game
    return game.model_copy(update={"moves": moves})


def _extract_subject_rating(game: Game, subject: PlayerColor) -> int | None:
    """Extract the subject's Elo from PGN headers (T017).

    Reads `WhiteElo`/`BlackElo` based on subject color, coerces to int,
    and clamps to [1, 3500]. Returns None for missing or unparseable
    values.
    """
    header_key = "WhiteElo" if subject is PlayerColor.WHITE else "BlackElo"
    raw = game.headers.get(header_key)
    if raw is None or raw == "":
        return None
    try:
        rating = int(raw)
    except (TypeError, ValueError):
        return None
    if rating < 1 or rating > 3500:
        return None
    return rating


def _hash_rating_baselines() -> str:
    """sha256 of the bundled rating baselines JSON, for the manifest."""
    if not BASELINES_PATH.is_file():
        return "0" * 64
    h = hashlib.sha256()
    h.update(BASELINES_PATH.read_bytes())
    return h.hexdigest()


def _analyse_positions(
    game: Game,
    analyzer: Analyzer,
    *,
    book: OpeningBook | None = None,
) -> tuple[Position, ...]:
    """Run the analyzer over the game's plies, marking book positions.

    `book` controls how `Position.is_book` is set:
      * `None` (default) → load the bundled book via
        `OpeningBook.load(OpeningBook.default_path())`.
      * An :class:`OpeningBook` instance (including
        :meth:`OpeningBook.empty`) → use as-is.
    """
    resolved_book = book if book is not None else _default_opening_book()
    board = chess.Board()
    positions: list[Position] = []
    positions.append(
        _attach_book_flag(analyzer.analyse(board, ply=0), board, resolved_book)
    )
    for ply, move in enumerate(game.moves, start=1):
        chess_move = chess.Move.from_uci(move.uci)
        if chess_move not in board.legal_moves:
            break
        board.push(chess_move)
        positions.append(
            _attach_book_flag(analyzer.analyse(board, ply=ply), board, resolved_book)
        )
    return tuple(positions)


def _attach_book_flag(
    position: Position,
    board: chess.Board,
    book: OpeningBook,
) -> Position:
    """Return `position` with `is_book` overridden to match the book lookup."""
    if book.is_empty:
        return position
    is_book = book.contains(board)
    if is_book == position.is_book:
        return position
    return position.model_copy(update={"is_book": is_book})


def _default_opening_book() -> OpeningBook:
    """Load the bundled book, falling back to an empty book on failure."""
    try:
        return OpeningBook.load(OpeningBook.default_path())
    except FileNotFoundError:
        return OpeningBook.empty()


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
