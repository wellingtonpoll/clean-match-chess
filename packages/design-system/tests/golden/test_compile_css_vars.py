"""Golden file for CSS-vars compile (T061)."""

from __future__ import annotations

from pathlib import Path

from design_system.tokens.compile_css_vars import DEFAULT_OUTPUT
from design_system.tokens.compile_weasyprint import compile_to_css
from design_system.tokens.loader import load_token_file


def test_css_vars_matches_committed_artefact() -> None:
    src = Path(__file__).resolve().parents[2] / "src" / "design_system" / "tokens" / "tokens.json"
    fresh = compile_to_css(load_token_file(src))
    assert fresh == Path(DEFAULT_OUTPUT).read_text(), (
        "css-vars compile drift: rerun `python -m design_system.tokens.compile_css_vars`"
    )
