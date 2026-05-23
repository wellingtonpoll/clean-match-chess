"""Catalogue v1.0.0 — JSON-driven entry validation (T075)."""

from __future__ import annotations

from design_system.components import catalogue

REQUIRED_ENTRIES = (
    "analytical-card",
    "risk-pill",
    "timeline",
    "heuristic-badge",
    "manifest-block",
    "code-inline",
)


def test_catalogue_loaded_from_json() -> None:
    assert catalogue.CATALOGUE_FILE.is_file()
    assert catalogue.CATALOGUE_FILE.suffix == ".json"


def test_every_required_entry_present() -> None:
    names = set(catalogue.names())
    for name in REQUIRED_ENTRIES:
        assert name in names, f"missing catalogue entry: {name}"


def test_every_entry_has_tokens_of_record() -> None:
    for name in REQUIRED_ENTRIES:
        comp = catalogue.get(name)
        assert comp.tokens_of_record, f"{name} has empty tokens_of_record"
        for token in comp.tokens_of_record:
            assert "." in token, f"{name}: token {token!r} missing namespace"


def test_every_entry_has_states() -> None:
    for name in REQUIRED_ENTRIES:
        comp = catalogue.get(name)
        assert comp.states, f"{name} has empty states"
        assert "default" in comp.states, f"{name} missing default state"


def test_every_entry_has_surfaces() -> None:
    valid = {"pdf", "html", "web"}
    for name in REQUIRED_ENTRIES:
        comp = catalogue.get(name)
        assert comp.surfaces, f"{name} has empty surfaces"
        assert comp.surfaces <= valid, f"{name} has invalid surfaces: {comp.surfaces}"


def test_every_entry_carries_accessibility() -> None:
    for name in REQUIRED_ENTRIES:
        comp = catalogue.get(name)
        assert comp.accessibility is not None, f"{name} missing accessibility"
        a11y = comp.accessibility
        assert hasattr(a11y, "aria_role")
        assert hasattr(a11y, "keyboard_focusable")


def test_timeline_supports_hover_state() -> None:
    timeline = catalogue.get("timeline")
    assert "hover" in timeline.states


def test_pdf_only_excluded_from_timeline() -> None:
    timeline = catalogue.get("timeline")
    assert "pdf" not in timeline.surfaces


def test_risk_pill_has_status_aria_role() -> None:
    pill = catalogue.get("risk-pill")
    assert pill.accessibility.aria_role == "status"


def test_analytical_card_has_region_role() -> None:
    card = catalogue.get("analytical-card")
    assert card.accessibility.aria_role == "region"


def test_manifest_block_has_table_role() -> None:
    block = catalogue.get("manifest-block")
    assert block.accessibility.aria_role == "table"


def test_added_in_is_semver() -> None:
    import re

    pattern = re.compile(r"^\d+\.\d+\.\d+$")
    for name in REQUIRED_ENTRIES:
        comp = catalogue.get(name)
        assert pattern.match(comp.added_in), f"{name}: bad added_in {comp.added_in!r}"
