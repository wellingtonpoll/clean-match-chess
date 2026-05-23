"""SC-005 WCAG contrast-pair regression (T085).

Each locked pair in `audits/wcag_pairs.json` MUST clear its minimum
ratio. Contrast is computed per WCAG 2.0 relative luminance:
    L = 0.2126 R + 0.7152 G + 0.0722 B
where each channel is sRGB-linearised. Contrast = (L_light + 0.05) /
(L_dark + 0.05).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from design_system.tokens.loader import load_token_file

WCAG_PAIRS_FILE: Final[Path] = (
    Path(__file__).resolve().parents[2] / "src" / "design_system" / "audits" / "wcag_pairs.json"
)
TOKENS_FILE: Final[Path] = (
    Path(__file__).resolve().parents[2] / "src" / "design_system" / "tokens" / "tokens.json"
)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    h = value.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _channel_linear(c: int) -> float:
    s = c / 255.0
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def _luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * _channel_linear(r) + 0.7152 * _channel_linear(g) + 0.0722 * _channel_linear(b)


def _contrast(fg_hex: str, bg_hex: str) -> float:
    lum_fg = _luminance(_hex_to_rgb(fg_hex))
    lum_bg = _luminance(_hex_to_rgb(bg_hex))
    light, dark = max(lum_fg, lum_bg), min(lum_fg, lum_bg)
    return (light + 0.05) / (dark + 0.05)


def test_wcag_pairs_file_loads() -> None:
    payload = json.loads(WCAG_PAIRS_FILE.read_text())
    assert payload["version"] == "1.0.0"
    assert payload["pairs"]


def test_every_pair_clears_minimum() -> None:
    tokens = load_token_file(TOKENS_FILE)
    payload = json.loads(WCAG_PAIRS_FILE.read_text())
    failures: list[str] = []
    for pair in payload["pairs"]:
        fg_hex = tokens.colours[pair["foreground"]].hex
        bg_hex = tokens.colours[pair["background"]].hex
        ratio = _contrast(fg_hex, bg_hex)
        if ratio < pair["min_ratio"]:
            failures.append(
                f"{pair['name']}: ratio {ratio:.2f} < min {pair['min_ratio']} "
                f"({pair['foreground']}={fg_hex} on {pair['background']}={bg_hex})"
            )
    assert not failures, "\n".join(failures)


def test_text_pairs_clear_aa_minimum() -> None:
    """Sanity: every text pair clears the WCAG AA 4.5 baseline."""
    tokens = load_token_file(TOKENS_FILE)
    payload = json.loads(WCAG_PAIRS_FILE.read_text())
    for pair in payload["pairs"]:
        if pair["kind"] != "text":
            continue
        fg_hex = tokens.colours[pair["foreground"]].hex
        bg_hex = tokens.colours[pair["background"]].hex
        assert _contrast(fg_hex, bg_hex) >= 4.5, pair["name"]
