"""Unit tests for feature 008 DB cache layer.

These tests cover the graceful-degradation paths + the URL-masking
helper — code that doesn't need a live Postgres. End-to-end behaviour
with real Postgres lives in `tests/integration/test_postgres_cache.py`.
"""

from __future__ import annotations

import pytest
from analysis_core.db import session as session_module
from analysis_core.db.cache import lookup, persist
from analysis_core.db.session import _mask_url, close_engine, get_session_factory, init_engine


@pytest.fixture(autouse=True)
def _reset_engine_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset module-level engine + clear DATABASE_URL before each test."""
    close_engine()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    yield
    close_engine()


class TestMaskUrl:
    def test_redacts_password(self) -> None:
        masked = _mask_url("postgresql+psycopg://user:secret@host:5432/db")
        assert "secret" not in masked
        assert "***" in masked
        assert "user" in masked
        assert "host" in masked
        assert "5432" in masked

    def test_passthrough_no_password(self) -> None:
        assert _mask_url("postgresql+psycopg://host/db") == "postgresql+psycopg://host/db"

    def test_unparseable_url(self) -> None:
        # urlsplit is tolerant; only truly broken URIs hit the fallback.
        # An empty string is parseable but yields no host.
        assert _mask_url("") == ""


class TestInitEngineGracefulDegradation:
    def test_no_database_url_returns_none_factory(self) -> None:
        # DATABASE_URL is unset by the autouse fixture.
        init_engine()
        assert get_session_factory() is None
        assert session_module._init_failure_reason == "DATABASE_URL not set"

    def test_explicit_unparseable_url(self) -> None:
        # SQLAlchemy raises ArgumentError (ValueError subclass) for bad URLs.
        init_engine("not-a-url")
        # init_engine swallows the error and leaves the factory None.
        assert get_session_factory() is None

    def test_idempotent_init(self) -> None:
        init_engine()  # first call: fails (no DATABASE_URL)
        init_engine()  # second call: no-op + does not re-fail
        assert get_session_factory() is None


class TestLookupGraceful:
    def test_lookup_without_database_returns_none(self) -> None:
        result = lookup(b"\x00" * 32, b"\x00" * 32)
        assert result is None

    def test_lookup_with_unreachable_url_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+psycopg://nobody:none@127.0.0.1:1/nope",
        )
        result = lookup(b"\xff" * 32, b"\xff" * 32)
        assert result is None


class TestPersistGraceful:
    def test_persist_without_database_no_raise(self) -> None:
        # AuditRun.model_dump is heavy; for the graceful path we never
        # actually serialise. Pass a sentinel typed-None which the guard
        # at the top of persist() handles before touching attributes.
        from unittest.mock import MagicMock

        audit_run = MagicMock()
        audit_run.manifest = None  # triggers the early-return guard
        manifest = MagicMock()
        # No DATABASE_URL → get_session_factory returns None → persist
        # returns immediately.
        persist(audit_run, manifest)  # no exception
