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
from heuristics.scoring.segment_aggregator import aggregate_segments
from heuristics.scoring.thresholds import SCORING_THRESHOLDS_VERSION
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

from analysis_core.db import cache as db_cache
from analysis_core.engine.analysis import Analyzer, EngineAnalyzer, StaticAnalyzer
from analysis_core.manifest import build_manifest, manifest_hash
from analysis_core.pipeline.cache import cleanmatch_home, persist_manifest
from analysis_core.pipeline.opening_book import OpeningBook
from analysis_core.pipeline.segmentation import segment_game

logger_db = __import__("structlog").get_logger("analysis_core.pipeline.cache_lookup")

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
    "regime-shift": "2.0.0",
    "behavioral-patterns": "2.0.0",
    "timing-analysis": "2.0.0",
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
    book_path: str | None = None,
    persist_root: Path | None = None,
    no_cache: bool = False,
) -> AuditRun:
    """Audit a single game (FR-019, T028).

    ``book_path`` opens an opening book by path:
      * ``None``   → bundled default book (FR-009).
      * ``""``     → no-op book (no positions marked in-book).
      * ``<path>`` → load polyglot file at ``<path>``.

    On book load failure (missing file, parse error) the audit falls back
    to the no-op book and continues.

    ``no_cache`` (feature 008): when True, skips both the Postgres cache
    lookup AND the persist. Otherwise: a `(pgn_sha256, manifest_sha256)`
    hit short-circuits the engine pipeline; a miss runs the full audit
    and persists the result via `analysis_core.db.cache.persist`.
    """
    book = _resolve_book(book_path)
    resolved_book_sha = book.sha256() if not book.is_empty else opening_book_sha256
    engine_command = _resolve_engine_command(engine_path, engine_image)

    resolved_engine = engine or (
        engine_fingerprint_from_path(engine_path) if engine_path else _default_engine_fp()
    )
    resolved_heuristics = heuristics or _default_heuristics()

    # Cache lookup (Phase 008/T014). Build a "preview" manifest containing
    # every field that contributes to `manifest_hash` so the hash matches
    # the manifest stamped inside `_build_run`. The remaining fields
    # (`started_at`, `host`) are explicitly excluded from `manifest_hash`,
    # so a hash collision is deterministic given identical inputs.
    if not no_cache:
        try:
            preview_manifest = build_manifest(
                engine=resolved_engine,
                heuristics=resolved_heuristics,
                input_pgn_sha256=game.pgn_sha256,
                opening_book_sha256=resolved_book_sha,
                design_system_version=design_system_version,
                rating_baselines_sha256=_hash_rating_baselines(),
                rating_baselines_version=get_baselines().version,
                scoring_thresholds_version=SCORING_THRESHOLDS_VERSION,
                signal_versions=dict(SIGNAL_VERSIONS),
            )
            pgn_sha256_bytes = bytes.fromhex(game.pgn_sha256)
            manifest_sha256_bytes = bytes.fromhex(manifest_hash(preview_manifest))
            cached = db_cache.lookup(pgn_sha256_bytes, manifest_sha256_bytes)
            if cached is not None:
                logger_db.info(
                    "db.cache.hit",
                    pgn_sha256=game.pgn_sha256[:16],
                    manifest_sha256=manifest_hash(preview_manifest)[:16],
                )
                return cached
        except (ValueError, AttributeError) as e:
            logger_db.warning("db.cache.preview_failed", error=str(e))

    if analyzer is None and engine_command:
        with EngineAnalyzer(engine_command) as ea:
            positions = _analyse_positions(game, ea, book=book)
            run = _build_run(
                game,
                positions,
                subject=subject,
                engine=resolved_engine,
                heuristics=resolved_heuristics,
                design_system_version=design_system_version,
                opening_book_sha256=resolved_book_sha,
                persist_root=persist_root,
            )
            if not no_cache and run.manifest is not None:
                db_cache.persist(run, run.manifest, game=game)
            return run

    analyzer = analyzer or StaticAnalyzer()
    positions = _analyse_positions(game, analyzer, book=book)
    run = _build_run(
        game,
        positions,
        subject=subject,
        engine=resolved_engine,
        heuristics=resolved_heuristics,
        design_system_version=design_system_version,
        opening_book_sha256=resolved_book_sha,
        persist_root=persist_root,
    )
    if not no_cache and run.manifest is not None:
        db_cache.persist(run, run.manifest, game=game)
    return run


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
    book_path: str | None = None,
    platform: str = "chesscom",
    no_cache: bool = False,
) -> AuditRun:
    """Audit a batch of games for one username. Builds AccountProfile.

    ``book_path`` semantics match ``run_single_game`` (T028).
    """
    engine_command = _resolve_engine_command(engine_path, engine_image)
    # Open one engine process for the entire batch.
    if analyzer is None and engine_command:
        resolved_engine = engine or (
            engine_fingerprint_from_path(engine_path) if engine_path else _default_engine_fp()
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
                    book_path=book_path,
                    no_cache=no_cache,
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
                book_path=book_path,
                no_cache=no_cache,
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
    raw_segments = segment_game(positions)

    subject_rating = _extract_subject_rating(game, subject)
    baselines = get_baselines()

    segment_score_value, _populated_segments = aggregate_segments(
        raw_segments,
        positions=positions,
        moves=moves,
        baselines=baselines,
        subject_rating=subject_rating,
        subject_color=subject,
    )

    # Game-level-only signals (per contracts/segment_score.contract.md):
    # regime-shift, precision-burst, complexity, tactical-detection,
    # engine-correlation/top3 run on the full game. The segment-weighted
    # score becomes a synthetic SignalAggregate fed into aggregate_score.
    _, top3, _ = engine_correlation(
        positions,
        moves,
        subject_rating=subject_rating,
        baselines=baselines,
    )

    signals: list[SignalAggregate] = []
    signals.append(complexity_score(positions))
    signals.append(tactical_density(positions))
    signals.append(regime_shift_score(positions, moves))
    signals.append(top3)
    signals.append(precision_burst(positions, moves))
    signals.append(_segment_weighted_signal(segment_score_value, len(moves)))

    def _resample_signals(
        sub_positions: tuple[Position, ...],
        sub_moves: tuple[Move, ...],
    ) -> tuple[SignalAggregate, ...]:
        """Recompute per-move signals on a bootstrapped subset (FR-007).

        Game-level signals (regime-shift) and segmentation-dependent
        signals are excluded — CUSUM and segment boundaries are not
        meaningful on a shuffled-with-replacement subset.
        """
        rs_top1, rs_top3, rs_weighted = engine_correlation(
            sub_positions,
            sub_moves,
            subject_rating=subject_rating,
            baselines=baselines,
        )
        return (
            complexity_score(sub_positions),
            tactical_density(sub_positions),
            rs_top1,
            rs_top3,
            rs_weighted,
            precision_burst(sub_positions, sub_moves),
            blunder_suppression(sub_positions, sub_moves),
            timing_anomaly(sub_positions, sub_moves),
            acpl_signal(
                positions=sub_positions,
                moves=sub_moves,
                subject_color=subject,
                subject_rating=subject_rating,
                baselines=baselines,
            ),
        )

    score = aggregate_score(
        tuple(signals),
        positions=positions,
        moves=moves,
        resample_signals=_resample_signals,
    )
    subject_player = _resolve_subject(game.players, subject)

    # FR-012 / SC-010: stamp opening-book + rating-baselines + per-signal
    # versions into the manifest. Schema fields added in feature 004.
    rating_baselines_sha256 = _hash_rating_baselines()
    rating_baselines_version = baselines.version
    signal_versions = dict(SIGNAL_VERSIONS)

    manifest = build_manifest(
        engine=engine,
        heuristics=heuristics,
        input_pgn_sha256=game.pgn_sha256,
        opening_book_sha256=opening_book_sha256,
        design_system_version=design_system_version,
        rating_baselines_sha256=rating_baselines_sha256,
        rating_baselines_version=rating_baselines_version,
        scoring_thresholds_version=SCORING_THRESHOLDS_VERSION,
        signal_versions=signal_versions,
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
        manifest=manifest,
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


def _segment_weighted_signal(score: float, samples: int) -> SignalAggregate:
    """Wrap the phase-weighted segment score in a SignalAggregate carrier.

    The signal_name matches the ``segments-weighted-aggregate`` entry in
    ``WEIGHTS`` so ``aggregate_score`` mixes it with the game-level-only
    signals.
    """
    clamped = max(0.0, min(1.0, float(score)))
    return SignalAggregate(
        signal_name="segments-weighted-aggregate",
        signal_version="1.0.0",
        mean=clamped,
        weighted_mean=clamped,
        samples=max(0, samples),
    )


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
    positions.append(_attach_book_flag(analyzer.analyse(board, ply=0), board, resolved_book))
    for ply, move in enumerate(game.moves, start=1):
        chess_move = chess.Move.from_uci(move.uci)
        if chess_move not in board.legal_moves:
            break
        board.push(chess_move)
        positions.append(_attach_book_flag(analyzer.analyse(board, ply=ply), board, resolved_book))
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


def _resolve_book(book_path: str | None) -> OpeningBook:
    """Map ``--book``/``book_path`` argument to an OpeningBook (T028).

    Convention:
      * ``None``    → bundled default book.
      * ``""``      → explicit no-op book (empty sentinel).
      * ``<path>``  → polyglot file at ``<path>``; falls back to empty
        book on failure.
    """
    if book_path is None:
        return _default_opening_book()
    if book_path == NO_BOOK_SENTINEL:
        return OpeningBook.empty()
    try:
        return OpeningBook.load(book_path)
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
