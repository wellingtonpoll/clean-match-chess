"""Registry registration, snapshot immutability, duplicate rejection."""

from __future__ import annotations

import pytest
from heuristics import registry
from shared_types.signal import HeuristicVersion


def _hv(name: str) -> HeuristicVersion:
    return HeuristicVersion(
        name=name,
        version="0.1.0",
        git_sha="abc1234",
        owner="cleanmatch",
        changelog_path="packages/heuristics/CHANGELOG.md",
    )


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    for name in ("signal-a", "signal-b", "signal-c"):
        registry.unregister(name)
    yield
    for name in ("signal-a", "signal-b", "signal-c"):
        registry.unregister(name)


def test_register_and_snapshot_alphabetical() -> None:
    registry.register(_hv("signal-b"), lambda: 0.0)
    registry.register(_hv("signal-a"), lambda: 0.0)
    snap = registry.snapshot()
    assert [r.version.name for r in snap] == ["signal-a", "signal-b"]


def test_snapshot_is_immutable_tuple() -> None:
    registry.register(_hv("signal-a"), lambda: 0.0)
    snap = registry.snapshot()
    assert isinstance(snap, tuple)
    with pytest.raises(AttributeError):
        snap.append(None)  # type: ignore[attr-defined]


def test_duplicate_registration_rejected() -> None:
    registry.register(_hv("signal-a"), lambda: 0.0)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(_hv("signal-a"), lambda: 0.0)


def test_lookup_returns_registered() -> None:
    registry.register(_hv("signal-a"), lambda: 0.42)
    found = registry.lookup("signal-a")
    assert found.version.name == "signal-a"
    assert found.fn() == 0.42


def test_lookup_unknown_raises() -> None:
    with pytest.raises(KeyError):
        registry.lookup("does-not-exist")


def test_versions_returns_versions_only() -> None:
    registry.register(_hv("signal-a"), lambda: 0.0)
    assert tuple(v.name for v in registry.versions()) == ("signal-a",)
