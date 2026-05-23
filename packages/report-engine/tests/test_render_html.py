"""HTML render determinism + content (T078)."""

from __future__ import annotations

from report_engine.render_html import render_report_html


def test_render_is_deterministic(bundle) -> None:
    one = render_report_html(bundle)
    two = render_report_html(bundle)
    assert one == two


def test_render_includes_manifest_version(bundle) -> None:
    html = render_report_html(bundle)
    assert "0.1.0" in html
    assert "Clean Match Chess" in html


def test_render_uses_metric_role_marker(bundle) -> None:
    html = render_report_html(bundle)
    assert 'data-role="metric-card-headline"' in html
