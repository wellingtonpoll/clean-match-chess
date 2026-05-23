"""Token loader (T008 + T010)."""

from __future__ import annotations

import pytest
from design_system.tokens.loader import LOCKED_EASING, TokenFile
from pydantic import ValidationError


def _base() -> dict:
    return {
        "version": "1.0.0",
        "name": "forensic-analytics",
        "colours": {
            "color.background": {"hex": "#0B0B0D"},
            "color.surface": {"hex": "#171717"},
            "color.text": {"hex": "#F5F5F2"},
            "color.signal": {"hex": "#F4D21F"},
            "color.amber": {"hex": "#F4B41F"},
            "color.muted": {"hex": "#A1A1AA"},
            "color.border": {"hex": "#2A2A2E"},
        },
        "spacing": {"1": 4, "2": 8, "3": 12, "4": 16, "5": 24, "6": 32, "7": 48, "8": 64},
        "radius": {"sm": 8, "md": 16, "lg": 24, "xl": 28},
        "motion_durations": {"fast": 200, "medium": 275, "slow": 350},
        "motion_easing": {"standard": LOCKED_EASING},
    }


def test_valid_token_file_parses() -> None:
    tf = TokenFile.model_validate(_base())
    assert tf.version == "1.0.0"
    assert tf.colours["color.signal"].hex == "#F4D21F"


def test_red_token_rejected() -> None:
    payload = _base()
    payload["colours"]["color.danger"] = {"hex": "#FF0000"}
    with pytest.raises(ValidationError, match="forbidden hue"):
        TokenFile.model_validate(payload)


def test_offset_spacing_rejected() -> None:
    payload = _base()
    payload["spacing"]["odd"] = 11
    with pytest.raises(ValidationError, match="spacing"):
        TokenFile.model_validate(payload)


def test_radius_out_of_range_rejected() -> None:
    payload = _base()
    payload["radius"]["lg"] = 40
    with pytest.raises(ValidationError, match="radius"):
        TokenFile.model_validate(payload)


def test_motion_duration_out_of_range_rejected() -> None:
    payload = _base()
    payload["motion_durations"]["too_slow"] = 500
    with pytest.raises(ValidationError, match="duration"):
        TokenFile.model_validate(payload)


def test_motion_easing_must_be_locked_curve() -> None:
    payload = _base()
    payload["motion_easing"]["standard"] = (0.0, 0.0, 1.0, 1.0)
    with pytest.raises(ValidationError, match="standard"):
        TokenFile.model_validate(payload)


def test_only_standard_easing_permitted() -> None:
    payload = _base()
    payload["motion_easing"]["bounce"] = (0.5, 1.5, 0.5, 1.5)
    with pytest.raises(ValidationError, match="only motion.easing.standard"):
        TokenFile.model_validate(payload)


def test_token_name_pattern_enforced() -> None:
    from design_system.tokens.loader import DesignToken
    from design_system.tokens.types import TokenCategory

    with pytest.raises(Exception):
        DesignToken(name="BAD.Name", category=TokenCategory.COLOUR)
