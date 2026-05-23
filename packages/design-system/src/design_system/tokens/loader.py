"""W3C DTCG token-file loader (T010).

Validates the locked rules from contracts/token-file-schema.md and the
constitution's forbidden-hue clause. Anything that doesn't conform
raises `TokenFileValidationError` at boot.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

from design_system.tokens.types import (
    ColourValue,
    TokenCategory,
    TypographyComposite,
)

LOCKED_SPACING: Final[frozenset[int]] = frozenset({4, 8, 12, 16, 24, 32, 48, 64})
LOCKED_RADIUS_LG_RANGE: Final[tuple[int, int]] = (20, 28)
LOCKED_MOTION_RANGE_MS: Final[tuple[int, int]] = (200, 350)
LOCKED_EASING: Final[tuple[float, float, float, float]] = (0.22, 1.0, 0.36, 1.0)

# Forbidden HSL hue range at saturation > 30% (0-100% range).
FORBIDDEN_HUE_RANGES: Final[tuple[tuple[float, float], ...]] = (
    (350.0, 360.0),
    (0.0, 20.0),
)
FORBIDDEN_SATURATION_THRESHOLD: Final[float] = 30.0


class TokenFileValidationError(ValueError):
    """Raised when tokens.json fails the locked rules."""


class DesignToken(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(pattern=r"^[a-z][a-z0-9]*(\.[a-z0-9_]+)*$")
    category: TokenCategory
    description: str = ""
    added_in: str = "0.1.0"


class TokenFile(BaseModel):
    """In-memory representation of tokens.json after schema validation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(pattern=r"^\d+\.\d+\.\d+(?:[-+].+)?$")
    name: str
    description: str = ""
    colours: dict[str, ColourValue] = Field(default_factory=dict)
    typography: dict[str, TypographyComposite] = Field(default_factory=dict)
    spacing: dict[str, int] = Field(default_factory=dict)
    radius: dict[str, int] = Field(default_factory=dict)
    motion_durations: dict[str, int] = Field(default_factory=dict)
    motion_easing: dict[str, tuple[float, float, float, float]] = Field(default_factory=dict)

    @field_validator("colours")
    @classmethod
    def _check_no_forbidden_hue(cls, value: dict[str, ColourValue]) -> dict[str, ColourValue]:
        for token_name, colour in value.items():
            hue, sat, _light = colour.hsl
            if sat > FORBIDDEN_SATURATION_THRESHOLD:
                for lo, hi in FORBIDDEN_HUE_RANGES:
                    if lo <= hue <= hi:
                        raise TokenFileValidationError(
                            f"colour token {token_name!r} ({colour.hex}) falls in "
                            f"forbidden hue range ({hue:.1f}deg, sat={sat:.1f}%); "
                            "no red allowed"
                        )
        return value

    @field_validator("spacing")
    @classmethod
    def _check_spacing_locked(cls, value: dict[str, int]) -> dict[str, int]:
        for name, px in value.items():
            if px not in LOCKED_SPACING:
                raise TokenFileValidationError(
                    f"spacing token {name!r}={px}px not in locked set {sorted(LOCKED_SPACING)}"
                )
        return value

    @field_validator("radius")
    @classmethod
    def _check_radius_large(cls, value: dict[str, int]) -> dict[str, int]:
        lo, hi = LOCKED_RADIUS_LG_RANGE
        for name in ("lg", "xl"):
            if name in value and not (lo <= value[name] <= hi):
                raise TokenFileValidationError(
                    f"radius token {name!r}={value[name]}px out of locked range {lo}-{hi}"
                )
        return value

    @field_validator("motion_durations")
    @classmethod
    def _check_motion_durations(cls, value: dict[str, int]) -> dict[str, int]:
        lo, hi = LOCKED_MOTION_RANGE_MS
        for name, ms in value.items():
            if not (lo <= ms <= hi):
                raise TokenFileValidationError(
                    f"motion.duration token {name!r}={ms}ms out of locked range {lo}-{hi}"
                )
        return value

    @field_validator("motion_easing")
    @classmethod
    def _check_motion_easing(
        cls, value: dict[str, tuple[float, float, float, float]]
    ) -> dict[str, tuple[float, float, float, float]]:
        if "standard" not in value:
            raise TokenFileValidationError(
                "motion.easing.standard is required; no other easing tokens are allowed"
            )
        if value["standard"] != LOCKED_EASING:
            raise TokenFileValidationError(
                f"motion.easing.standard must equal {LOCKED_EASING}; got {value['standard']}"
            )
        if set(value.keys()) - {"standard"}:
            raise TokenFileValidationError(
                f"only motion.easing.standard is permitted; extra: {set(value) - {'standard'}}"
            )
        return value


def load_token_file(path: Path) -> TokenFile:
    """Load + validate a tokens.json file from disk."""
    payload = json.loads(path.read_text())
    return TokenFile.model_validate(payload)


def parse_token_file(payload: dict[str, Any]) -> TokenFile:
    """Validate an in-memory payload as a TokenFile."""
    return TokenFile.model_validate(payload)


__all__ = [
    "FORBIDDEN_HUE_RANGES",
    "FORBIDDEN_SATURATION_THRESHOLD",
    "LOCKED_EASING",
    "LOCKED_MOTION_RANGE_MS",
    "LOCKED_RADIUS_LG_RANGE",
    "LOCKED_SPACING",
    "DesignToken",
    "TokenFile",
    "TokenFileValidationError",
    "load_token_file",
    "parse_token_file",
]
