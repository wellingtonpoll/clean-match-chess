"""Golden file for Framer Motion variants compile (T064)."""

from __future__ import annotations

from pathlib import Path

from design_system.tokens.compile_framer_motion import (
    DEFAULT_OUTPUT,
    DEFAULT_TOKEN_FILE,
    compile_to_ts,
)
from design_system.tokens.loader import load_token_file


def test_compile_matches_committed_variants() -> None:
    fresh = compile_to_ts(load_token_file(DEFAULT_TOKEN_FILE))
    assert fresh == Path(DEFAULT_OUTPUT).read_text(), (
        "framer-motion compile drift: rerun `python -m design_system.tokens.compile_framer_motion`"
    )


def test_variants_export_standard_easing() -> None:
    fresh = compile_to_ts(load_token_file(DEFAULT_TOKEN_FILE))
    assert "standard:" in fresh
    assert "[0.22, 1.0, 0.36, 1.0]" in fresh
