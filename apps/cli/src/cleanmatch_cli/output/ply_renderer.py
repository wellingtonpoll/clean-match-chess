"""Per-ply detail renderer (T075).

Enforces SC-003 invariant: when the ply is flagged, the rendered detail
MUST cite >= 1 move, >= 1 signal, and >= 1 principle. The renderer
returns a list of lines AND a structured invariant report so the show
command can validate it.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared_types.game import Move, Position


@dataclass(frozen=True, slots=True)
class PlyInvariantReport:
    """SC-003 invariant evidence for one flagged ply."""

    move_count: int
    signal_count: int
    principle_count: int

    @property
    def passes(self) -> bool:
        return self.move_count >= 1 and self.signal_count >= 1 and self.principle_count >= 1


def render_ply(
    ply: int,
    move: Move,
    position: Position,
) -> tuple[list[str], PlyInvariantReport]:
    """Render ply detail. Returns (lines, invariant report)."""
    lines: list[str] = []
    lines.append(
        f"Ply {ply + 1}   {move.san}   played by {move.played_by.value}"
        + (f" (used {move.time_spent_ms} ms)" if move.time_spent_ms else "")
    )
    lines.append("")

    complexity = position.complexity.composite if position.complexity else 0.0
    lines.append(
        f"Position complexity: {complexity:.3f}"
        + (
            (
                f"  (branching={position.complexity.branching_factor:.2f}  "
                f"volatility={position.complexity.eval_volatility:.2f}  "
                f"tactical_density={position.complexity.tactical_density:.2f})"
            )
            if position.complexity
            else ""
        )
    )

    lines.append("Engine top moves:")
    for cm in position.top_moves:
        marker = "*" if cm.uci == move.uci else " "
        eval_str = f"{cm.eval_cp:+d}" if cm.eval_cp is not None else "mate"
        lines.append(f"  {marker} {cm.rank}. {cm.san:<10}  eval={eval_str}")

    cited_signals = list(move.signal_contributions)
    if cited_signals:
        lines.append("")
        lines.append("Signal contributions:")
        for c in cited_signals:
            lines.append(
                f"  {c.signal_name}@{c.signal_version}  value={c.value:.3f}  "
                f"weight={c.weight:.3f}  rationale={c.rationale!r}"
            )

    principles: list[str] = []
    if position.is_only_move:
        principles.append("Principle 5: forced move, low weight")
    if position.is_book:
        principles.append("Principle 6: opening theory, discounted")
    if position.is_critical and not position.is_only_move:
        principles.append("Principle 7: complexity-weighted contribution")
    if principles:
        lines.append("")
        lines.append("Cited principles:")
        for p in principles:
            lines.append(f"  - {p}")

    lines.append("")
    lines.append("This is a probabilistic assessment, not an accusation.")

    invariant = PlyInvariantReport(
        move_count=1,
        signal_count=len(cited_signals),
        principle_count=len(principles),
    )
    return lines, invariant
