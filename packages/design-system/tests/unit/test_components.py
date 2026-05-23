"""Component catalogue + risk-treatment invariants (T015 + T017)."""

from __future__ import annotations

import pytest
from design_system.components import catalogue, risk_treatments
from design_system.tokens.types import RiskLevel


def test_catalogue_contains_required_components() -> None:
    required = {
        "analytical-card",
        "risk-pill",
        "timeline",
        "heuristic-badge",
        "manifest-block",
        "code-inline",
    }
    assert required <= set(catalogue.names())


def test_every_token_of_record_starts_with_namespace() -> None:
    for comp in catalogue.COMPONENTS.values():
        for token in comp.tokens_of_record:
            assert "." in token, f"token {token!r} in {comp.name} missing namespace dot"


def test_risk_treatments_locked_levels() -> None:
    levels = {t.level for t in risk_treatments.ALL}
    assert levels == {RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH}


def test_risk_high_uses_color_signal() -> None:
    high = risk_treatments.HIGH
    fg = next(b for b in high.bindings if b.role == "foreground")
    assert fg.token_name == "color.signal"


def test_risk_medium_uses_color_amber() -> None:
    medium = risk_treatments.MEDIUM
    fg = next(b for b in medium.bindings if b.role == "foreground")
    assert fg.token_name == "color.amber"


def test_no_risk_treatment_references_red_token() -> None:
    for t in risk_treatments.ALL:
        for b in t.bindings:
            assert "red" not in b.token_name.lower()
            assert "danger" not in b.token_name.lower()


def test_every_risk_treatment_carries_glyph() -> None:
    """Monochrome / colour-blind fallback per audits.md CHK037."""
    for t in risk_treatments.ALL:
        assert t.glyph, f"risk treatment {t.level} missing glyph"


def test_role_markers_locked() -> None:
    for t in risk_treatments.ALL:
        assert t.role_marker_html == "risk-pill"
        assert t.role_marker_pdf == "Risk-Pill"


def test_get_unknown_component_raises() -> None:
    with pytest.raises(KeyError):
        catalogue.get("does-not-exist")
