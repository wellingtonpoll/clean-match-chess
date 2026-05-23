"""Human and JSON renderers for command output.

Contract (constitution III, contracts/cli-*.md):
- JSON renderer writes to stdout (machine-parseable single document).
- Human renderer also writes to stdout but in a fixed, scannable layout.
- Logs always go to stderr (see `output.logging`).
"""

from __future__ import annotations

import json
import sys
from enum import StrEnum
from typing import Any


class OutputFormat(StrEnum):
    HUMAN = "human"
    JSON = "json"


def render(payload: dict[str, Any], fmt: OutputFormat) -> None:
    """Write `payload` to stdout in the requested format."""
    if fmt is OutputFormat.JSON:
        json.dump(payload, sys.stdout, sort_keys=True, separators=(",", ":"), default=str)
        sys.stdout.write("\n")
    else:
        _write_human(payload)
    sys.stdout.flush()


def _write_human(payload: dict[str, Any]) -> None:
    for key, value in payload.items():
        if isinstance(value, dict):
            sys.stdout.write(f"{key}:\n")
            for k, v in value.items():
                sys.stdout.write(f"  {k}: {v}\n")
        elif isinstance(value, list | tuple):
            sys.stdout.write(f"{key}: {', '.join(str(v) for v in value)}\n")
        else:
            sys.stdout.write(f"{key}: {value}\n")
