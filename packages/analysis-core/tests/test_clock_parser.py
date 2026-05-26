"""Tests for `analysis_core.ingest._clock_parser`."""

from __future__ import annotations

import pytest
from analysis_core.ingest._clock_parser import parse_clock_ms, parse_time_control


class TestParseClockMs:
    def test_simple_minute_second(self) -> None:
        assert parse_clock_ms("[%clk 0:09:55]") == 9 * 60 * 1000 + 55 * 1000

    def test_with_hours(self) -> None:
        assert parse_clock_ms("[%clk 1:23:45]") == (1 * 3600 + 23 * 60 + 45) * 1000

    def test_fractional_half_second(self) -> None:
        assert parse_clock_ms("[%clk 0:00:30.5]") == 30_500

    def test_fractional_three_digits(self) -> None:
        assert parse_clock_ms("[%clk 0:00:30.555]") == 30_555

    def test_fractional_one_digit_pads(self) -> None:
        # `.5` should mean 500 ms, not 5 ms.
        assert parse_clock_ms("[%clk 0:00:30.5]") == 30_500

    def test_zero(self) -> None:
        assert parse_clock_ms("[%clk 0:00:00]") == 0

    def test_returns_none_when_no_clock(self) -> None:
        assert parse_clock_ms("just a comment") is None
        assert parse_clock_ms("") is None
        assert parse_clock_ms(None) is None

    def test_finds_clock_among_other_annotations(self) -> None:
        # Lichess sometimes adds %eval before %clk.
        comment = "[%eval -0.23] [%clk 0:04:12.3]"
        assert parse_clock_ms(comment) == 4 * 60 * 1000 + 12 * 1000 + 300

    def test_malformed_returns_none(self) -> None:
        assert parse_clock_ms("[%clk abc:def:ghi]") is None
        assert parse_clock_ms("[%clk]") is None


class TestParseTimeControl:
    def test_simple_seconds(self) -> None:
        assert parse_time_control("600") == (600, 0)

    def test_with_increment(self) -> None:
        assert parse_time_control("600+5") == (600, 5)
        assert parse_time_control("180+1") == (180, 1)
        assert parse_time_control("60+0") == (60, 0)

    def test_correspondence(self) -> None:
        assert parse_time_control("1/86400") == (86400, 0)

    def test_unset(self) -> None:
        assert parse_time_control(None) == (0, 0)
        assert parse_time_control("") == (0, 0)

    def test_unknown_returns_zero(self) -> None:
        assert parse_time_control("garbage") == (0, 0)
        assert parse_time_control("abc+def") == (0, 0)

    @pytest.mark.parametrize(
        ("tc", "expected"),
        [
            ("3600", (3600, 0)),
            ("3600+30", (3600, 30)),
            ("60+0", (60, 0)),
        ],
    )
    def test_parametric(self, tc: str, expected: tuple[int, int]) -> None:
        assert parse_time_control(tc) == expected
