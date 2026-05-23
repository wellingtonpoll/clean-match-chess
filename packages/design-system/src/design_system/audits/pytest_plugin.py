"""Pytest plugin registering the four audit marks (T020)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

_AUDIT_MARKS: tuple[tuple[str, str], ...] = (
    ("audit_palette", "design-system palette audit"),
    ("audit_typography", "design-system typography audit"),
    ("audit_motion", "design-system motion audit"),
    ("audit_lexical", "design-system lexical audit"),
)


def pytest_configure(config: pytest.Config) -> None:
    for name, description in _AUDIT_MARKS:
        config.addinivalue_line("markers", f"{name}: {description}")


def audit_marks() -> tuple[str, ...]:
    return tuple(name for name, _ in _AUDIT_MARKS)
