"""Monochrome / colour-blind glyph fallback (T087 — CHK037).

Every `RiskTreatment` MUST carry a distinct glyph so a reader with
deuteranopia (or a monochrome PDF print) can disambiguate LOW /
MEDIUM / HIGH without relying on hue. The glyph is the structural
encoding; colour is supplementary.
"""

from __future__ import annotations

from design_system.components import catalogue
from design_system.components.risk_treatments import ALL, BY_LEVEL
from design_system.tokens.types import RiskLevel


def test_every_treatment_carries_a_glyph() -> None:
    for t in ALL:
        assert t.glyph, f"risk treatment {t.level} missing glyph"


def test_glyphs_are_pairwise_distinct() -> None:
    glyphs = {t.glyph for t in ALL}
    assert len(glyphs) == len(ALL), f"glyph collision: {[t.glyph for t in ALL]}"


def test_low_uses_open_circle() -> None:
    assert BY_LEVEL[RiskLevel.LOW].glyph == "○"


def test_medium_uses_half_circle() -> None:
    assert BY_LEVEL[RiskLevel.MEDIUM].glyph == "◐"


def test_high_uses_filled_circle() -> None:
    assert BY_LEVEL[RiskLevel.HIGH].glyph == "●"


def test_risk_pill_catalogue_entry_supports_glyph_fallback() -> None:
    """The risk-pill component MUST be reachable on every surface so
    the glyph fallback renders everywhere — including PDF (monochrome
    print) and HTML (deuteranopia)."""
    pill = catalogue.get("risk-pill")
    assert "pdf" in pill.surfaces
    assert "html" in pill.surfaces
    assert "web" in pill.surfaces


def test_role_marker_locked_for_every_treatment() -> None:
    """Without the role marker, the glyph alone cannot be located by
    assistive tech; the role marker carries the semantic anchor."""
    for t in ALL:
        assert t.role_marker_html == "risk-pill"
        assert t.role_marker_pdf == "Risk-Pill"
