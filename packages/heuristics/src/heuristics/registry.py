"""Versioned heuristic signal registry.

Each signal module registers itself on import via `register()`. The
registry returns a frozen snapshot (immutable tuple) so a single
audit run cannot be mutated mid-flight.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from shared_types.signal import HeuristicVersion

# Callable shape kept open in MVP; pipeline (Phase 3 US1) will tighten it.
SignalCallable = Callable[..., float]


@dataclass(frozen=True, slots=True)
class RegisteredSignal:
    version: HeuristicVersion
    fn: SignalCallable


_REGISTRY: dict[str, RegisteredSignal] = {}


def register(version: HeuristicVersion, fn: SignalCallable) -> None:
    """Register a signal. Duplicate names are rejected."""
    if version.name in _REGISTRY:
        raise ValueError(f"signal {version.name!r} already registered")
    _REGISTRY[version.name] = RegisteredSignal(version=version, fn=fn)


def unregister(name: str) -> None:
    """Used by tests to keep the registry hermetic across cases."""
    _REGISTRY.pop(name, None)


def snapshot() -> tuple[RegisteredSignal, ...]:
    """Return an immutable snapshot of all currently registered signals."""
    return tuple(sorted(_REGISTRY.values(), key=lambda r: r.version.name))


def versions() -> tuple[HeuristicVersion, ...]:
    return tuple(rs.version for rs in snapshot())


def lookup(name: str) -> RegisteredSignal:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"signal {name!r} not registered") from exc
