"""Cache-layer public API: `lookup` + `persist`.

Feature 008. Both functions handle DB-down gracefully (warn + skip, no
raise) per FR-004. The audit pipeline calls them unconditionally around
a real engine run; if Postgres is unreachable, behaviour falls back to
"no cache, run analysis at full cost".

Sync (not async) to match the synchronous audit pipeline. See
`session.py` for the rationale.
"""

from __future__ import annotations

from typing import Any

import structlog
from shared_types.audit_run import AuditRun
from shared_types.game import Game
from shared_types.report import ReproducibilityManifest
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from analysis_core.db.models import AuditRunModel
from analysis_core.db.session import get_session_factory
from analysis_core.manifest import manifest_hash

logger = structlog.get_logger(__name__)


def _risk_level_str(audit_run: AuditRun) -> str | None:
    """Return the string form of the audit's risk level (handles enum + str)."""
    if audit_run.score is None or audit_run.score.risk_level is None:
        return None
    rl = audit_run.score.risk_level
    return rl.value if hasattr(rl, "value") else str(rl)


def _headers(game: Game | None) -> dict[str, Any]:
    """Pull queryable columns out of a Game for indexing.

    AuditRun itself only carries game IDs (`games: tuple[str, ...]`) — the
    full Game object is held by the pipeline and is passed to persist()
    so the indexed columns get populated. None is acceptable; columns
    fall back to NULL.
    """
    if game is None:
        return {
            "white_username": None,
            "black_username": None,
            "platform": None,
            "game_id": None,
            "ply_count": None,
        }
    headers = game.headers if isinstance(game.headers, dict) else {}
    return {
        "white_username": headers.get("White"),
        "black_username": headers.get("Black"),
        "platform": game.source,
        "game_id": game.id,
        "ply_count": game.ply_count,
    }


def lookup(pgn_sha256: bytes, manifest_sha256: bytes) -> AuditRun | None:
    """Return the cached `AuditRun` for this `(pgn, manifest)` pair, or None.

    None covers all three negative cases (cache disabled, DB unreachable,
    cache miss) so callers always treat it as "go run the analysis".
    """
    factory = get_session_factory()
    if factory is None:
        return None

    try:
        with factory() as session:
            stmt = (
                select(AuditRunModel.run_json)
                .where(AuditRunModel.pgn_sha256 == pgn_sha256)
                .where(AuditRunModel.manifest_sha256 == manifest_sha256)
                .limit(1)
            )
            payload = session.execute(stmt).scalar_one_or_none()
            if payload is None:
                return None
            try:
                return AuditRun.model_validate(payload)
            except (ValueError, TypeError) as e:
                logger.warning(
                    "db.cache.deserialize_failed",
                    error=str(e),
                    pgn_sha256=pgn_sha256.hex()[:16],
                )
                return None
    except OperationalError as e:
        logger.warning("db.cache.lookup_unreachable", error=str(e))
        return None
    except SQLAlchemyError as e:
        logger.warning("db.cache.lookup_failed", error=str(e))
        return None


def persist(
    audit_run: AuditRun,
    manifest: ReproducibilityManifest,
    *,
    game: Game | None = None,
) -> None:
    """Persist the AuditRun. ON CONFLICT DO NOTHING — idempotent.

    Failures are swallowed + logged. The audit result is already in
    memory; not caching it is unfortunate but not a user-visible error.
    """
    factory = get_session_factory()
    if factory is None:
        return

    if not audit_run.manifest or not audit_run.manifest.input_pgn_sha256:
        logger.debug("db.cache.persist_skipped", reason="manifest.input_pgn_sha256 missing")
        return

    try:
        pgn_sha256 = bytes.fromhex(audit_run.manifest.input_pgn_sha256)
        manifest_sha256 = bytes.fromhex(manifest_hash(manifest))
    except (AttributeError, ValueError) as e:
        logger.warning("db.cache.persist_key_failed", error=str(e))
        return

    headers = _headers(game)
    run_json = audit_run.model_dump(mode="json")
    manifest_json = manifest.model_dump(mode="json")

    try:
        with factory() as session:
            stmt = (
                pg_insert(AuditRunModel)
                .values(
                    pgn_sha256=pgn_sha256,
                    manifest_sha256=manifest_sha256,
                    platform=headers["platform"],
                    game_id=headers["game_id"],
                    white_username=headers["white_username"],
                    black_username=headers["black_username"],
                    score=audit_run.score.score if audit_run.score is not None else None,
                    risk_level=_risk_level_str(audit_run),
                    ply_count=headers["ply_count"],
                    run_json=run_json,
                    manifest_json=manifest_json,
                )
                .on_conflict_do_nothing(index_elements=["pgn_sha256", "manifest_sha256"])
            )
            session.execute(stmt)
            session.commit()
    except OperationalError as e:
        logger.warning("db.cache.persist_unreachable", error=str(e))
    except SQLAlchemyError as e:
        logger.warning("db.cache.persist_failed", error=str(e))
