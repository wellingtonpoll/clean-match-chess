"""Plain-language rationale templates (T059)."""

from __future__ import annotations

import re

import pytest
from heuristics.scoring.narrative import RATIONALE_TEMPLATES, rationale_for

FORBIDDEN_TERMS = re.compile(
    r"\b(cheater|cheating|guilty|fraud|fraudster|criminal|trapaceiro|trapa[cç]a)\b",
    re.IGNORECASE,
)


@pytest.mark.parametrize("name", list(RATIONALE_TEMPLATES))
def test_every_template_renders(name: str) -> None:
    out = rationale_for(name, 0.42)
    assert "{value" not in out


@pytest.mark.parametrize("name", list(RATIONALE_TEMPLATES))
def test_no_accusatory_language(name: str) -> None:
    out = rationale_for(name, 0.99)
    assert FORBIDDEN_TERMS.search(out) is None


def test_unknown_signal_gets_generic_fallback() -> None:
    out = rationale_for("does-not-exist", 0.5)
    assert "does-not-exist" in out


def test_every_known_signal_has_a_template() -> None:
    expected = {
        "engine-correlation/top1",
        "engine-correlation/top3",
        "engine-correlation/weighted",
        "complexity-analysis",
        "tactical-detection",
        "regime-shift",
        "behavioral-patterns/precision-burst",
        "behavioral-patterns/blunder-suppression",
        "timing-analysis",
    }
    assert expected.issubset(RATIONALE_TEMPLATES.keys())
