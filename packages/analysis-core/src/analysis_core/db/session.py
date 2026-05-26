"""SQLAlchemy engine + session factory for the analysis cache.

Feature 008. The engine is a process-global singleton initialised lazily
via `init_engine()`. `get_session_factory()` returns `None` when no
`DATABASE_URL` is set or initial connection failed — callers (the cache
layer) treat `None` as the graceful-degradation signal.

Sync (not async) on purpose: the audit pipeline at `pipeline.run` is
already synchronous; bridging async/sync here would just add layers
without buying anything (the cache is invoked once at the start and once
at the end of an audit, not in a streaming hot loop).

Password masking: `_mask_url()` redacts the password component via
`urllib.parse.urlsplit` so credentials never escape into structured logs
(Principle III + FR-004).
"""

from __future__ import annotations

import os
from typing import Final
from urllib.parse import SplitResult, urlsplit, urlunsplit

import structlog
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

logger = structlog.get_logger(__name__)

_DEV_URL: Final[str] = "postgresql+psycopg://cleanmatch:cleanmatch@localhost:5432/cleanmatch"

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_init_attempted: bool = False
_init_failure_reason: str | None = None


def _mask_url(url: str) -> str:
    """Redact the password from a SQLAlchemy URL for safe logging."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "<unparseable>"
    if not parts.password:
        return url
    redacted_netloc = parts.hostname or ""
    if parts.username:
        redacted_netloc = f"{parts.username}:***@{redacted_netloc}"
    if parts.port:
        redacted_netloc = f"{redacted_netloc}:{parts.port}"
    redacted = SplitResult(
        scheme=parts.scheme,
        netloc=redacted_netloc,
        path=parts.path,
        query=parts.query,
        fragment=parts.fragment,
    )
    return urlunsplit(redacted)


def init_engine(url: str | None = None) -> None:
    """Initialise the engine + session factory. Idempotent."""
    global _engine, _session_factory, _init_attempted, _init_failure_reason

    if _session_factory is not None:
        return

    resolved = url or os.environ.get("DATABASE_URL")
    if not resolved:
        _init_attempted = True
        _init_failure_reason = "DATABASE_URL not set"
        logger.debug("db.cache.disabled", reason=_init_failure_reason)
        return

    try:
        engine = create_engine(
            resolved,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=2,
            echo=False,
            future=True,
        )
    except (SQLAlchemyError, ValueError) as e:
        _init_attempted = True
        _init_failure_reason = f"engine construction failed: {e}"
        logger.warning(
            "db.cache.disabled",
            reason=_init_failure_reason,
            url=_mask_url(resolved),
        )
        return

    _engine = engine
    _session_factory = sessionmaker(engine, expire_on_commit=False, future=True)
    _init_attempted = True
    _init_failure_reason = None
    logger.debug("db.cache.engine_initialised", url=_mask_url(resolved))


def get_session_factory() -> sessionmaker[Session] | None:
    """Return the session factory, or None if the cache is disabled."""
    if _session_factory is None and not _init_attempted:
        init_engine()
    return _session_factory


def close_engine() -> None:
    """Dispose of the engine. For test teardown + clean shutdown."""
    global _engine, _session_factory, _init_attempted, _init_failure_reason
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
    _init_attempted = False
    _init_failure_reason = None
