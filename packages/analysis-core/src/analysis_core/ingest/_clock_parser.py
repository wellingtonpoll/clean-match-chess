"""Per-move clock annotation parser for chess.com / Lichess PGNs.

PGN comments such as `{ [%clk 0:09:55] }` (or `{ [%clk 0:09:55.5] }` with
sub-second precision) carry the remaining clock for the side that just
moved. Both chess.com and Lichess emit this annotation by default on
online games. The format is the de-facto standard from
https://www.enpassant.dk/chess/palview/enhancedpgn.htm.

This module extracts the clock value from a single comment string and
returns it as integer milliseconds. The diff against the prior clock
(plus any `TimeControl` increment) is what produces `Move.time_spent_ms`
— that arithmetic lives in `pgn_loader._extract_moves`.

This is a pure-regex module with no PGN-library coupling; tests at
`packages/analysis-core/tests/test_clock_parser.py` cover the format
variants we need to handle.
"""

from __future__ import annotations

import re
from typing import Final

_CLK_RE: Final[re.Pattern[str]] = re.compile(r"\[%clk\s+(\d+):(\d+):(\d+)(?:\.(\d+))?\]")


def parse_clock_ms(comment: str | None) -> int | None:
    """Return the clock value (ms) embedded in a PGN comment, or None.

    Examples:
        >>> parse_clock_ms("[%clk 0:09:55]")
        595000
        >>> parse_clock_ms("[%clk 1:23:45]")
        5025000
        >>> parse_clock_ms("[%clk 0:00:30.5]")
        30500
        >>> parse_clock_ms(None) is None
        True
        >>> parse_clock_ms("no clock here") is None
        True
    """
    if not comment:
        return None
    m = _CLK_RE.search(comment)
    if m is None:
        return None
    hours = int(m.group(1))
    minutes = int(m.group(2))
    seconds = int(m.group(3))
    fractional = m.group(4)
    total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000
    if fractional is not None:
        # `0.5` → 500 ms; `0.55` → 550 ms; `0.555` → 555 ms.
        # Pad/truncate to exactly 3 digits.
        padded = (fractional + "000")[:3]
        total_ms += int(padded)
    return total_ms


def parse_time_control(tc_header: str | None) -> tuple[int, int]:
    """Parse a PGN `TimeControl` header into (initial_seconds, increment_seconds).

    Recognised forms (chess.com / Lichess):
      * `600` → (600, 0)
      * `600+5` → (600, 5)
      * `180+1` → (180, 1)
      * `1/86400` → (86400, 0) (correspondence — single move per N seconds)
      * unknown / unset → (0, 0)
    """
    if not tc_header:
        return (0, 0)
    tc = tc_header.strip()
    # Correspondence: `moves/seconds` form. We collapse to one cycle.
    if "/" in tc:
        try:
            _, secs = tc.split("/", 1)
            return (int(secs), 0)
        except ValueError:
            return (0, 0)
    if "+" in tc:
        try:
            initial, inc = tc.split("+", 1)
            return (int(initial), int(inc))
        except ValueError:
            return (0, 0)
    try:
        return (int(tc), 0)
    except ValueError:
        return (0, 0)
