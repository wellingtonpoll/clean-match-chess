"""HTML report renderer (T085).

Uses Jinja2 with autoescape on. The template is loaded from this
package's `templates/` directory. Output is deterministic given the
same input bundle.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from shared_types.report import ReportBundle

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "j2", "html.j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_report_html(bundle: ReportBundle) -> str:
    template = _env.get_template("single_game.html.j2")
    return template.render(_build_context(bundle))


def _build_context(bundle: ReportBundle) -> dict[str, object]:
    manifest = bundle.manifest
    score = None
    flagged_segments = bundle.narrative.flagged_segments
    risk_label = "LOW"
    risk_level_class = "low"
    score_value = 0.0
    ci_low = 0.0
    ci_high = 0.0
    dominant: list[str] = []

    if bundle.narrative.flagged_segments:
        risk_label = "MEDIUM/HIGH"
        risk_level_class = "high"

    fs_payload = [
        {
            "phase": fs.segment.phase.value,
            "start": fs.segment.ply_range[0],
            "end": fs.segment.ply_range[1],
            "headline": fs.headline,
        }
        for fs in flagged_segments
    ]

    # Pull score from manifest-adjacent path: caller bundles run separately;
    # MVP renders without an explicit score block by leaving zeros above.
    return {
        "language": bundle.language.value,
        "run_id_short": bundle.run_id[:8],
        "created_at": manifest.started_at.isoformat(),
        "design_system_version": manifest.design_system_version,
        "analysis_core_version": manifest.analysis_core_version,
        "engine_name": manifest.engine_name,
        "engine_version": manifest.engine_version,
        "engine_sha": manifest.engine_binary_sha256,
        "input_pgn_sha": manifest.input_pgn_sha256,
        "opening_book_sha": manifest.opening_book_sha256,
        "summary_paragraph": bundle.narrative.summary_paragraph,
        "dominant_signals": dominant,
        "flagged_segments": fs_payload,
        "score": score_value,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "risk_label": risk_label,
        "risk_level_class": risk_level_class,
        "_": score,
    }
