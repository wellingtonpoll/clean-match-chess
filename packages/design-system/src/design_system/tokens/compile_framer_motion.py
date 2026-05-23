"""Compile tokens.json -> Framer Motion variants TS (T065)."""

from __future__ import annotations

from pathlib import Path

from design_system.tokens.loader import TokenFile, load_token_file

DEFAULT_TOKEN_FILE: Path = Path(__file__).resolve().parent / "tokens.json"
DEFAULT_OUTPUT: Path = (
    Path(__file__).resolve().parents[3] / "adapters" / "framer-motion" / "variants.ts"
)


def compile_to_ts(tokens: TokenFile) -> str:
    lines: list[str] = []
    lines.append(f"// Generated from tokens v{tokens.version} - DO NOT EDIT.")
    lines.append("export const easing = {")
    for name, curve in sorted(tokens.motion_easing.items()):
        a, b, c, d = curve
        lines.append(f"  {name}: [{a}, {b}, {c}, {d}] as const,")
    lines.append("} as const;")
    lines.append("")
    lines.append("export const duration = {")
    for name, ms in sorted(tokens.motion_durations.items()):
        lines.append(f"  {name}: {ms / 1000},  // seconds")
    lines.append("} as const;")
    lines.append("")
    lines.append("export const variants = {")
    lines.append("  fadeIn: {")
    lines.append("    hidden: { opacity: 0 },")
    lines.append("    visible: {")
    lines.append("      opacity: 1,")
    lines.append("      transition: { duration: duration.medium, ease: easing.standard },")
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


__all__ = ["DEFAULT_OUTPUT", "DEFAULT_TOKEN_FILE", "compile_to_file", "compile_to_ts"]
