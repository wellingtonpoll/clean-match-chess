"""Timeline renderer: one line per ply (T074)."""

from __future__ import annotations

from shared_types.audit_run import AuditRun
from shared_types.game import Game, Position
from shared_types.score import SuspicionScore


def render_timeline(
    run: AuditRun,
    game: Game,
    positions: tuple[Position, ...],
    score: SuspicionScore,
) -> list[str]:
    """Render a timeline. Returns one string per output line."""
    lines: list[str] = []
    subject = run.subject
    lines.append(
        f"Run {run.id[:8]}  {subject.username or '<unknown>'} ({subject.color.value})  "
        f"engine={run.engine.name} {run.engine.version}"
    )
    lines.append("")
    lines.append("ply  move           class             complexity  flag  signals")
    lines.append("-" * 72)

    for idx, mv in enumerate(game.moves):
        if idx >= len(positions):
            break
        pos = positions[idx]
        complexity = pos.complexity.composite if pos.complexity else 0.0
        flag = "*" if pos.is_critical and not pos.is_only_move else " "
        signal_names = ", ".join(c.signal_name for c in mv.signal_contributions) or "-"
        lines.append(
            f"{idx + 1:>3}  {mv.san:<14} {mv.classification.value:<17} "
            f"{complexity:>10.3f}  {flag:^4}  {signal_names}"
        )

    lines.append("")
    lines.append(
        f"Score: {score.score:.3f}  Risk: {score.risk_level.value.upper()}  "
        f"CI: ({score.confidence_interval[0]:.3f}, {score.confidence_interval[1]:.3f})"
    )
    if score.dominant_signals:
        lines.append("Dominant signals: " + ", ".join(score.dominant_signals))
    return lines
