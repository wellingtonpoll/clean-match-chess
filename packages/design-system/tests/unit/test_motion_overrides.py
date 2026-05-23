"""Motion-override parser + expiry rule (T069)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from design_system.audits.motion_overrides import (
    DEFAULT_OVERRIDES_FILE,
    MotionOverridesError,
    check_expiry,
    load_overrides,
)


def test_default_overrides_file_is_empty_initially() -> None:
    assert load_overrides() == ()


def test_overrides_root_must_be_list(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"overrides": "not-a-list"}))
    with pytest.raises(MotionOverridesError, match="list"):
        load_overrides(bad)


def test_missing_field_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"overrides": [{"file": "x.css"}]}))
    with pytest.raises(MotionOverridesError, match="missing required field"):
        load_overrides(bad)


def test_expiry_in_past_marked_expired(tmp_path: Path) -> None:
    expired = (date.today() - timedelta(days=1)).isoformat()
    good = tmp_path / "ov.json"
    good.write_text(
        json.dumps(
            {
                "overrides": [
                    {
                        "file": "components/spinner.css",
                        "selector": ".spinner",
                        "reason": "spec exception",
                        "reviewer": "@alice",
                        "expiry": expired,
                    }
                ]
            }
        )
    )
    overrides = load_overrides(good)
    expired_list = check_expiry(overrides)
    assert len(expired_list) == 1


def test_future_expiry_not_expired(tmp_path: Path) -> None:
    future = (date.today() + timedelta(days=30)).isoformat()
    good = tmp_path / "ov.json"
    good.write_text(
        json.dumps(
            {
                "overrides": [
                    {
                        "file": "components/spinner.css",
                        "selector": ".spinner",
                        "reason": "spec exception",
                        "reviewer": "@alice",
                        "expiry": future,
                    }
                ]
            }
        )
    )
    overrides = load_overrides(good)
    assert check_expiry(overrides) == []


def test_default_overrides_path_exists() -> None:
    assert DEFAULT_OVERRIDES_FILE.is_file()
