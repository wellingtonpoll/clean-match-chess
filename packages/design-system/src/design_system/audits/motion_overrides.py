"""Motion override parser (T069 contract).

Documented exception list to the locked motion curve / duration range.
Each override carries: file, selector, reason, reviewer, expiry (ISO
date). Expired overrides fail the audit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

DEFAULT_OVERRIDES_FILE: Final[Path] = Path(__file__).parent / "motion_overrides.json"


@dataclass(frozen=True, slots=True)
class MotionOverride:
    file: str
    selector: str
    reason: str
    reviewer: str
    expiry_iso: str

    @property
    def is_expired(self) -> bool:
        return date.fromisoformat(self.expiry_iso) < date.today()


class MotionOverridesError(ValueError):
    """Raised when overrides file is malformed or contains expired entries."""


def load_overrides(path: Path | None = None) -> tuple[MotionOverride, ...]:
    src = path or DEFAULT_OVERRIDES_FILE
    payload = json.loads(src.read_text())
    raw_overrides = payload.get("overrides", [])
    if not isinstance(raw_overrides, list):
        raise MotionOverridesError(f"overrides field must be a list in {src}")

    out: list[MotionOverride] = []
    for idx, entry in enumerate(raw_overrides):
        if not isinstance(entry, dict):
            raise MotionOverridesError(f"override #{idx} must be an object")
        try:
            out.append(
                MotionOverride(
                    file=str(entry["file"]),
                    selector=str(entry["selector"]),
                    reason=str(entry["reason"]),
                    reviewer=str(entry["reviewer"]),
                    expiry_iso=str(entry["expiry"]),
                )
            )
        except KeyError as exc:
            raise MotionOverridesError(f"override #{idx} missing required field {exc}") from exc
        except ValueError as exc:
            raise MotionOverridesError(f"override #{idx} expiry not ISO date: {exc}") from exc
    return tuple(out)


def check_expiry(overrides: tuple[MotionOverride, ...]) -> list[MotionOverride]:
    """Return overrides whose expiry is in the past."""
    return [ov for ov in overrides if ov.is_expired]


__all__ = [
    "DEFAULT_OVERRIDES_FILE",
    "MotionOverride",
    "MotionOverridesError",
    "check_expiry",
    "load_overrides",
]
