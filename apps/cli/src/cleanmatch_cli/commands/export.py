"""`cleanmatch export <run-id>` subcommand (T091)."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

from analysis_core.pipeline.cache import cleanmatch_home
from report_engine.bundle import write_bundle
from report_engine.lexical_audit import LexicalAuditError
from report_engine.render_html import render_report_html
from report_engine.render_json import render_report_json
from report_engine.render_pdf import render_report_pdf
from shared_types.audit_run import AuditRun
from shared_types.game import Game
from shared_types.report import (
    HostInfo,
    Narrative,
    ReportBundle,
    ReportFormat,
    ReportLanguage,
    ReproducibilityManifest,
)
from shared_types.score import SuspicionScore

from cleanmatch_cli.output.exit_codes import ExitCode


def execute(
    run_id: str,
    *,
    format_: str,
    out: str | None,
    language: str,
) -> ExitCode:
    run_dir = cleanmatch_home() / "runs" / run_id
    if not run_dir.is_dir():
        sys.stderr.write(f"error: run {run_id!r} not found under {run_dir}.\n")
        return ExitCode.USER_ERROR

    try:
        run = AuditRun.model_validate_json((run_dir / "run.json").read_text())
        game = Game.model_validate_json((run_dir / "game.json").read_text())
        score = SuspicionScore.model_validate_json((run_dir / "score.json").read_text())
        manifest = _load_or_synthesize_manifest(run_dir, run, game)
    except FileNotFoundError as exc:
        sys.stderr.write(f"error: run directory missing file: {exc}\n")
        return ExitCode.UPSTREAM_ERROR

    try:
        lang = ReportLanguage(language)
    except ValueError:
        sys.stderr.write(f"error: --language {language!r} not supported.\n")
        return ExitCode.USER_ERROR

    bundle = ReportBundle(
        run_id=run.id,
        formats=frozenset({ReportFormat.PDF, ReportFormat.HTML, ReportFormat.JSON}),
        language=lang,
        narrative=Narrative(
            summary_paragraph=_summary_for(score, language),
            flagged_segments=(),
        ),
        manifest=manifest,
    )

    out_path = Path(out) if out else Path(f"./cleanmatch-{run_id}.zip")
    try:
        if format_ == "bundle":
            artefacts = write_bundle(bundle, out_path)
            sys.stdout.write(f"{artefacts.archive_path}\n")
        elif format_ == "html":
            out_path.write_text(render_report_html(bundle))
            sys.stdout.write(f"{out_path}\n")
        elif format_ == "json":
            out_path.write_text(render_report_json(bundle))
            sys.stdout.write(f"{out_path}\n")
        elif format_ == "pdf":
            render_report_pdf(bundle, out_path)
            sys.stdout.write(f"{out_path}\n")
        else:
            sys.stderr.write(
                f"error: --format {format_!r} unsupported; use bundle/html/json/pdf.\n"
            )
            return ExitCode.USER_ERROR
    except LexicalAuditError as exc:
        sys.stderr.write(f"error: render failed lexical audit: {exc}\n")
        return ExitCode.INTERNAL_ERROR
    except OSError as exc:
        sys.stderr.write(f"error: could not write {out_path}: {exc}\n")
        return ExitCode.USER_ERROR

    return ExitCode.SUCCESS


def _summary_for(score: SuspicionScore, language: str) -> str:
    risk = score.risk_level.value.upper()
    if language == "pt":
        return (
            f"Pontuação probabilística: {score.score:.3f}. Risco: {risk}. "
            f"IC 95%: ({score.confidence_interval[0]:.3f}, "
            f"{score.confidence_interval[1]:.3f}). Esta é uma avaliação "
            "probabilística, não uma alegação."
        )
    return (
        f"Probabilistic score: {score.score:.3f}. Risk: {risk}. "
        f"95% CI: ({score.confidence_interval[0]:.3f}, "
        f"{score.confidence_interval[1]:.3f}). This is a probabilistic "
        "assessment, not an accusation."
    )


def _load_or_synthesize_manifest(
    run_dir: Path,
    run: AuditRun,
    game: Game,
) -> ReproducibilityManifest:
    manifest_path = run_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            return ReproducibilityManifest.model_validate_json(manifest_path.read_text())
        except Exception:
            sys.stderr.write(
                "warning: persisted manifest unreadable; synthesizing one for export.\n"
            )

    return ReproducibilityManifest(
        engine_name=run.engine.name,
        engine_version=run.engine.version,
        engine_binary_sha256=run.engine.binary_sha256,
        engine_uci_options=run.engine.uci_options,
        heuristics=run.heuristic_set,
        analysis_core_version="0.1.0",
        report_engine_version="0.1.0",
        python_chess_version="1.999",
        opening_book_sha256="0" * 64,
        input_pgn_sha256=game.pgn_sha256,
        started_at=datetime.now(UTC),
        host=HostInfo(os="unknown", arch="unknown", cpu_model="unknown", ram_bytes=0),
        design_system_version="0.1.0",
    )
