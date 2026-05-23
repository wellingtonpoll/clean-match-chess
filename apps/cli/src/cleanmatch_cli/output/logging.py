"""structlog configuration: pretty (stderr) and JSON formatters.

Controlled by `--log-format` / `--log-level` flags and the env vars
CLEANMATCH_LOG_FORMAT and CLEANMATCH_LOG_LEVEL (constitution III).
All logs go to stderr; stdout is reserved for user-facing renderers.
"""

from __future__ import annotations

import logging
import os
import sys
from enum import StrEnum
from typing import Final

import structlog

LOG_FORMAT_ENV: Final[str] = "CLEANMATCH_LOG_FORMAT"
LOG_LEVEL_ENV: Final[str] = "CLEANMATCH_LOG_LEVEL"


class LogFormat(StrEnum):
    PRETTY = "pretty"
    JSON = "json"


class LogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


_LEVELS = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARN: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
}


def configure(
    fmt: LogFormat | None = None,
    level: LogLevel | None = None,
) -> None:
    """Idempotent structlog configuration honouring CLI flags + env."""
    fmt = fmt or LogFormat(os.environ.get(LOG_FORMAT_ENV, LogFormat.PRETTY.value))
    level = level or LogLevel(os.environ.get(LOG_LEVEL_ENV, LogLevel.INFO.value))

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    if fmt is LogFormat.JSON:
        processors.append(structlog.processors.JSONRenderer(sort_keys=True))
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=False))

    logging.basicConfig(
        stream=sys.stderr,
        level=_LEVELS[level],
        format="%(message)s",
    )
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(_LEVELS[level]),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
