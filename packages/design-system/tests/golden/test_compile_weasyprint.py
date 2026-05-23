"""Golden-file test for WeasyPrint adapter (T026)."""

from __future__ import annotations

from pathlib import Path

from design_system.tokens.compile_weasyprint import (
    DEFAULT_OUTPUT,
    DEFAULT_TOKEN_FILE,
    compile_to_css,
)
from design_system.tokens.loader import load_token_file


def test_compile_matches_committed_artefact() -> None:
    """Recompiling tokens.json MUST produce the committed CSS byte-for-byte."""
    tokens = load_token_file(DEFAULT_TOKEN_FILE)
    fresh = compile_to_css(tokens)
    committed = Path(DEFAULT_OUTPUT).read_text()
    assert fresh == committed, (
        "compile drift detected: rerun `python -m design_system.tokens.compile_weasyprint`"
    )


def test_compile_emits_root_block() -> None:
    tokens = load_token_file(DEFAULT_TOKEN_FILE)
    css = compile_to_css(tokens)
    assert css.startswith("/* Generated from tokens v1.0.0")
    assert ":root {" in css
    assert "--color-signal: #F4D21F" in css


def test_compile_excludes_disallowed_features() -> None:
    tokens = load_token_file(DEFAULT_TOKEN_FILE)
    css = compile_to_css(tokens)
    for forbidden in ("display: grid", ":has(", "container-type", "inset-block"):
        assert forbidden not in css
