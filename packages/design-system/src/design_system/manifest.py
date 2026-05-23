"""Manifest field producer (T022 satisfied by feature 001).

`ReproducibilityManifest.design_system_version` (in
`packages/shared-types/src/shared_types/report.py`) already requires a
semver-pattern field. This module exposes the canonical helper consumers
should use rather than reading `__version__` directly, so the manifest
producer is the single integration point.
"""

from __future__ import annotations

from design_system.version import __version__


def current_version() -> str:
    """Return the design-system semver as it should appear in manifests."""
    return __version__


__all__ = ["current_version"]
