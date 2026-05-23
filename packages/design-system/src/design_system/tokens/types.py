"""Enums and polymorphic value classes for design tokens (T011)."""

from __future__ import annotations

import colorsys
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TokenCategory(StrEnum):
    COLOUR = "colour"
    TYPOGRAPHY = "typography"
    SPACING = "spacing"
    RADIUS = "radius"
    SHADOW = "shadow"
    MOTION = "motion"
    Z_INDEX = "z_index"
    CHART_SERIES = "chart_series"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ColourValue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    hex: str = Field(pattern=r"^#[0-9A-F]{6}$")

    @property
    def hsl(self) -> tuple[float, float, float]:
        r = int(self.hex[1:3], 16) / 255.0
        g = int(self.hex[3:5], 16) / 255.0
        b = int(self.hex[5:7], 16) / 255.0
        h, lightness, s = colorsys.rgb_to_hls(r, g, b)
        # Return hue in degrees, saturation + lightness in 0..100 percent
        return (h * 360.0, s * 100.0, lightness * 100.0)


class TypographyComposite(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    font_family: str
    font_weight: int = Field(ge=100, le=900)
    font_size: str
    line_height: float = Field(gt=0)
    letter_spacing: str | None = None


class ShadowComposite(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    offset_x: str
    offset_y: str
    blur: str
    colour: str


class MotionComposite(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    duration_ms: int = Field(ge=200, le=350)
    easing_ref: str


class CubicBezierValue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    points: tuple[float, float, float, float]


class DimensionValue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    px: float
