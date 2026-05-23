"""Deuteranopia regression on the 6-series chart palette (T086).

Simulates deuteranopia using the Machado 2009 severity-1.0 matrix
applied to sRGB, then computes CIE76 Delta-E between every pair of
simulated colours in Lab space (via colormath). The minimum pairwise
distance MUST stay above the threshold floor; this is a regression
check, not an absolute readability claim.

Note: signal (`color.signal`, #F4D21F) and amber (`color.amber`,
#F4B41F) are deliberately neighbouring yellows because they encode
HIGH vs MEDIUM risk on the same surface. Their structural
disambiguation is the glyph + role marker on the risk-pill component,
not colour. With deuteranopia they collapse to a CIE76 distance near
~9.4. The threshold below preserves the current state and protects
against any future drift that would make the palette MORE confusable.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Final

import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore", SyntaxWarning)
    from colormath.color_conversions import convert_color
    from colormath.color_objects import LabColor, sRGBColor

CHART_SERIES_KEYS: Final[tuple[str, ...]] = tuple(f"color.chart_series.{i}" for i in range(1, 7))
MIN_DELTA_E: Final[float] = 9.0

DEUTERANOPIA_MATRIX: Final[tuple[tuple[float, ...], ...]] = (
    (0.367322, 0.860646, -0.227968),
    (0.280085, 0.672501, 0.047413),
    (-0.011820, 0.042940, 0.968881),
)


def _simulate(hex_value: str) -> sRGBColor:
    h = hex_value.lstrip("#")
    r, g, b = int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0
    m = DEUTERANOPIA_MATRIX
    new_r = max(0.0, min(1.0, m[0][0] * r + m[0][1] * g + m[0][2] * b))
    new_g = max(0.0, min(1.0, m[1][0] * r + m[1][1] * g + m[1][2] * b))
    new_b = max(0.0, min(1.0, m[2][0] * r + m[2][1] * g + m[2][2] * b))
    return sRGBColor(new_r, new_g, new_b)


def _to_lab(rgb: sRGBColor) -> LabColor:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return convert_color(rgb, LabColor)


def _delta_e_cie76(a: LabColor, b: LabColor) -> float:
    return ((a.lab_l - b.lab_l) ** 2 + (a.lab_a - b.lab_a) ** 2 + (a.lab_b - b.lab_b) ** 2) ** 0.5


def _chart_palette() -> list[str]:
    tokens_path = (
        Path(__file__).resolve().parents[2] / "src" / "design_system" / "tokens" / "tokens.json"
    )
    payload = json.loads(tokens_path.read_text())
    colours = payload["colours"]
    return [colours[k]["hex"] for k in CHART_SERIES_KEYS]


def test_chart_palette_has_six_series() -> None:
    palette = _chart_palette()
    assert len(palette) == 6


def test_min_pairwise_delta_e_above_floor() -> None:
    palette = _chart_palette()
    labs = [_to_lab(_simulate(h)) for h in palette]
    min_distance = float("inf")
    worst_pair: tuple[str, str] = ("", "")
    for i in range(len(labs)):
        for j in range(i + 1, len(labs)):
            d = _delta_e_cie76(labs[i], labs[j])
            if d < min_distance:
                min_distance = d
                worst_pair = (palette[i], palette[j])
    assert min_distance >= MIN_DELTA_E, (
        f"deuteranopia regression: closest pair {worst_pair} dist {min_distance:.2f}"
        f" < floor {MIN_DELTA_E}"
    )


@pytest.mark.parametrize(
    ("expected", "hex_in"),
    [
        ("#F4D21F", "#F4D21F"),
        ("#F4B41F", "#F4B41F"),
    ],
)
def test_simulation_is_deterministic(expected: str, hex_in: str) -> None:
    rgb1 = _simulate(hex_in)
    rgb2 = _simulate(hex_in)
    assert rgb1.rgb_r == rgb2.rgb_r
    assert rgb1.rgb_g == rgb2.rgb_g
    assert rgb1.rgb_b == rgb2.rgb_b
    _ = expected  # placeholder: confirms parametrize wiring
