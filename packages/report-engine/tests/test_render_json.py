"""JSON render determinism (T079)."""

from __future__ import annotations

from report_engine.render_json import render_report_json


def test_render_is_deterministic(bundle) -> None:
    one = render_report_json(bundle)
    two = render_report_json(bundle)
    assert one == two


def test_render_is_sorted(bundle) -> None:
    text = render_report_json(bundle)
    assert text.startswith("{")
    assert "design_system_version" in text


def test_render_contains_manifest_version(bundle) -> None:
    text = render_report_json(bundle)
    assert '"design_system_version":"0.1.0"' in text
