"""CLI exit-code map (constitution Principle III).

0 success
1 user error (invalid input, unknown flag, unsupported variant)
2 upstream failure (chess.com, Stockfish, opening book)
3 internal bug (caught exception)
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    USER_ERROR = 1
    UPSTREAM_ERROR = 2
    INTERNAL_ERROR = 3


def for_error_code(code: str) -> ExitCode:
    """Map shared_types.RunErrorCode (string) to ExitCode."""
    mapping = {
        "user_error": ExitCode.USER_ERROR,
        "upstream_error": ExitCode.UPSTREAM_ERROR,
        "internal_error": ExitCode.INTERNAL_ERROR,
    }
    try:
        return mapping[code]
    except KeyError as exc:
        raise KeyError(f"unknown run-error code: {code!r}") from exc
