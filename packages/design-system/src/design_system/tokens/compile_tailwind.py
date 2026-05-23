"""Compile tokens.json -> Tailwind v4 theme.ts (T060).

Tailwind v4 reads `@theme` blocks in CSS or a typed theme module. This
compiler emits the typed TS object so frontend code can import it.
"""

from __future__ import annotations

from pathlib import Path

from design_system.tokens.loader import TokenFile, load_token_file

DEFAULT_TOKEN_FILE: Path = Path(__file__).resolve().parent / "tokens.json"
DEFAULT_OUTPUT: Path = Path(__file__).resolve().parents[3] / "adapters" / "tailwind" / "theme.ts"


def compile_to_ts(tokens: TokenFile) -> str:
    lines: list[str] = []
    lines.append(f"// Generated from tokens v{tokens.version} - DO NOT EDIT.")
    lines.append("export const theme = {")
    lines.append("  colors: {")
    for name, c in sorted(tokens.colours.items()):
        lines.append(f'    {_key(name)}: "{c.hex}",')
    lines.append("  },")
    lines.append("  spacing: {")
    for name, px in sorted(tokens.spacing.items()):
        lines.append(f'    "{name}": "{px}px",')
    lines.append("  },")
    lines.append("  radius: {")
    for name, px in sorted(tokens.radius.items()):
        lines.append(f'    {name}: "{px}px",')
    lines.append("  },")
    lines.append("  motion: {")
    lines.append("    duration: {")
    for name, ms in sorted(tokens.motion_durations.items()):
        lines.append(f'      {name}: "{ms}ms",')
    lines.append("    },")
    lines.append("    easing: {")
    for name, curve in sorted(tokens.motion_easing.items()):
        a, b, c2, d = curve
        lines.append(f'      {name}: "cubic-bezier({a}, {b}, {c2}, {d})",')
    lines.append("    },")
    lines.append("  },")
    lines.append("  typography: {")
    for name, t in sorted(tokens.typography.items()):
        nice = name.split(".", 1)[1]
        lines.append(f"    {nice}: {{")
        lines.append(f'      fontFamily: "{t.font_family}",')
        lines.append(f"      fontWeight: {t.font_weight},")
        lines.append(f'      fontSize: "{t.font_size}",')
        lines.append(f"      lineHeight: {t.line_height},")
        if t.letter_spacing is not None:
            lines.append(f'      letterSpacing: "{t.letter_spacing}",')
        lines.append("    },")
    lines.append("  },")
    lines.append("} as const;")
    lines.append("")
    return "\n".join(lines)


def compile_to_file(
    token_file: Path | None = None,
    output: Path | None = None,
) -> Path:
    src = token_file or DEFAULT_TOKEN_FILE
    dst = output or DEFAULT_OUTPUT
    tokens = load_token_file(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(compile_to_ts(tokens))
    return dst


def _key(token_name: str) -> str:
    """Map a dotted token name to a JS-safe key (quoted for dots)."""
    return f'"{token_name}"'


__all__ = [
    "DEFAULT_OUTPUT",
    "DEFAULT_TOKEN_FILE",
    "compile_to_file",
    "compile_to_ts",
]
