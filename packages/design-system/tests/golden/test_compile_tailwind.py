"""Golden file for Tailwind theme.ts compile (T059)."""

from __future__ import annotations

from pathlib import Path

from design_system.tokens.compile_tailwind import (
    DEFAULT_OUTPUT,
    DEFAULT_TOKEN_FILE,
    compile_to_ts,
)
from design_system.tokens.loader import load_token_file


def test_compile_matches_committed_theme() -> None:
    fresh = compile_to_ts(load_token_file(DEFAULT_TOKEN_FILE))
    assert fresh == Path(DEFAULT_OUTPUT).read_text(), (
        "tailwind compile drift: rerun `python -m design_system.tokens.compile_tailwind`"
    )


def test_theme_exposes_signal_color() -> None:
    fresh = compile_to_ts(load_token_file(DEFAULT_TOKEN_FILE))
    assert '"color.signal": "#F4D21F"' in fresh
