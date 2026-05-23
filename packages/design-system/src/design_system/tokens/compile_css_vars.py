"""Compile tokens.json -> generic :root CSS variables (T062).

Identical to the WeasyPrint compiler at present; lives in a separate
module so future adapter divergence (e.g., per-theme blocks) is
trivial without disturbing the PDF artefact.
"""

from __future__ import annotations

from pathlib import Path

from design_system.tokens.compile_weasyprint import compile_to_css
from design_system.tokens.loader import load_token_file

DEFAULT_TOKEN_FILE: Path = Path(__file__).resolve().parent / "tokens.json"
DEFAULT_OUTPUT: Path = Path(__file__).resolve().parents[3] / "adapters" / "css-vars" / "tokens.css"


def compile_to_file(
    token_file: Path | None = None,
    output: Path | None = None,
) -> Path:
    src = token_file or DEFAULT_TOKEN_FILE
    dst = output or DEFAULT_OUTPUT
    tokens = load_token_file(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(compile_to_css(tokens))
    return dst


__all__ = ["DEFAULT_OUTPUT", "DEFAULT_TOKEN_FILE", "compile_to_file"]
