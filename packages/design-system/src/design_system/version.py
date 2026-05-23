"""Single source of truth for the design-system semver (FR-016)."""

from __future__ import annotations

from importlib import metadata

try:
    __version__ = metadata.version("design-system")
except metadata.PackageNotFoundError:
    __version__ = "0.0.0+local"

__all__ = ["__version__"]
