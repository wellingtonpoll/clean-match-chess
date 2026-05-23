"""Compile tokens.json -> WeasyPrint-subset CSS (T029).

The generated CSS uses only features in the WeasyPrint 60+ subset:
flexbox, tables, custom properties. No Grid, no :has(), no container
queries, no inset-block-*, no subgrid.

Output is byte-deterministic given the same input TokenFile.
"""

from __future__ import annotations

from pathlib import Path

from design_system.tokens.loader import TokenFile, load_token_file

DEFAULT_TOKEN_FILE: Path = Path(__file__).resolve().parent / "tokens.json"
DEFAULT_OUTPUT: Path = (
    Path(__file__).resolve().parents[3] / "adapters" / "weasyprint" / "tokens.css"
)


def compile_to_css(tokens: TokenFile) -> str:
    """Render `tokens` as WeasyPrint-subset CSS string."""
    lines: list[str] = []
    lines.append(f"/* Generated from tokens v{tokens.version} - DO NOT EDIT. */")
    lines.append(":root {")

    for name, colour in sorted(tokens.colours.items()):
        lines.append(f"  --{_var(name)}: {colour.hex};")

    for name, px in sorted(tokens.spacing.items()):
        lines.append(f"  --spacing-{name}: {px}px;")

    for name, px in sorted(tokens.radius.items()):
        lines.append(f"  --radius-{name}: {px}px;")

    for name, ms in sorted(tokens.motion_durations.items()):
        lines.append(f"  --motion-duration-{name}: {ms}ms;")

    for name, curve in sorted(tokens.motion_easing.items()):
        a, b, c, d = curve
        lines.append(f"  --motion-easing-{name}: cubic-bezier({a}, {b}, {c}, {d});")

    for name, t in sorted(tokens.typography.items()):
        prefix = f"--typography-{_var(name)}"
        lines.append(f"  {prefix}-family: {t.font_family};")
        lines.append(f"  {prefix}-weight: {t.font_weight};")
        lines.append(f"  {prefix}-size: {t.font_size};")
        lines.append(f"  {prefix}-line-height: {t.line_height};")
        if t.letter_spacing is not None:
            lines.append(f"  {prefix}-letter-spacing: {t.letter_spacing};")

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def compile_to_file(
    token_file: Path | None = None,
    output: Path | None = None,
) -> Path:
    """Compile the bundled tokens.json and write the CSS artefact."""
    src = token_file or DEFAULT_TOKEN_FILE
    dst = output or DEFAULT_OUTPUT
    tokens = load_token_file(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(compile_to_css(tokens))
    return dst


def _var(token_name: str) -> str:
    """Convert dotted token name to a CSS variable suffix."""
    return token_name.replace(".", "-")


__all__ = [
    "DEFAULT_OUTPUT",
    "DEFAULT_TOKEN_FILE",
    "compile_to_css",
    "compile_to_file",
]
