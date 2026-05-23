"""Manifest determinism + design_system_version field."""

from __future__ import annotations

from datetime import UTC, datetime

from analysis_core.manifest import manifest_hash


def test_manifest_hash_excludes_started_at_and_host(manifest_factory) -> None:
    a = manifest_factory(started_at=datetime(2026, 5, 23, 12, 0, tzinfo=UTC))
    b = manifest_factory(started_at=datetime(2030, 1, 1, 0, 0, tzinfo=UTC))
    assert manifest_hash(a) == manifest_hash(b)


def test_manifest_hash_changes_on_input_pgn(manifest_factory) -> None:
    a = manifest_factory(input_pgn_sha256="1" * 64)
    b = manifest_factory(input_pgn_sha256="2" * 64)
    assert manifest_hash(a) != manifest_hash(b)


def test_manifest_hash_changes_on_design_system_version(manifest_factory) -> None:
    a = manifest_factory(design_system_version="1.0.0")
    b = manifest_factory(design_system_version="1.1.0")
    assert manifest_hash(a) != manifest_hash(b)


def test_manifest_includes_design_system_version(manifest_factory) -> None:
    m = manifest_factory(design_system_version="1.2.3")
    assert m.design_system_version == "1.2.3"
