"""Integration helpers between report-engine and design-system (T050)."""

from __future__ import annotations

from pathlib import Path


def get_weasyprint_css_path() -> Path:
    """Path to the committed WeasyPrint adapter CSS from design-system."""
    return (
        Path(__file__).resolve().parents[4]
        / "packages"
        / "design-system"
        / "adapters"
        / "weasyprint"
        / "tokens.css"
    )


def get_design_system_version() -> str:
    """Single integration point for the design-system semver."""
    from design_system.version import __version__

    return __version__
