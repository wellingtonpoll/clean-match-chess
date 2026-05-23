"""Report bundle zipper (T090).

Zips the three rendered formats + manifest + README into a single
deliverable archive. Runs the lexical audit on the HTML and JSON
renders before writing the zip; a finding raises `LexicalAuditError`
so the export CLI can map it to an internal-error exit code.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from shared_types.report import ReportBundle

from report_engine.lexical_audit import LexicalAuditError, audit_text
from report_engine.render_html import render_report_html
from report_engine.render_json import render_report_json
from report_engine.render_pdf import render_report_pdf


@dataclass(frozen=True, slots=True)
class BundleArtefacts:
    archive_path: Path
    html_path: Path
    json_path: Path
    pdf_path: Path
    manifest_path: Path
    readme_path: Path


_README_BODY = """Clean Match Chess — Auditable Report Bundle
============================================

This bundle is a self-contained record of one audit run.

Files:
- report.pdf       Human-readable forensic report.
- report.html      Same report in HTML form.
- report.json      Machine-readable structured data.
- manifest.json    Reproducibility manifest (engine, heuristics, hashes).

To reproduce:
  pipx install cleanmatch (or your project install)
  cleanmatch audit-game <original.pgn>
  cleanmatch export <run-id> --out ./reproduction.zip
  diff <(unzip -p original.zip report.json) \
       <(unzip -p reproduction.zip report.json)

On the same CPU architecture, the diff MUST be empty.

This document is probabilistic. It is not an accusation.
"""


def write_bundle(bundle: ReportBundle, dest: Path) -> BundleArtefacts:
    """Produce a zip archive at `dest` containing all four artefacts."""
    work = dest.parent
    work.mkdir(parents=True, exist_ok=True)

    html = render_report_html(bundle)
    html_findings = audit_text(html)
    if html_findings:
        raise LexicalAuditError(html_findings)

    json_text = render_report_json(bundle)
    json_findings = audit_text(json_text)
    if json_findings:
        raise LexicalAuditError(json_findings)

    html_path = work / "report.html"
    html_path.write_text(html)

    json_path = work / "report.json"
    json_path.write_text(json_text)

    pdf_path = work / "report.pdf"
    render_report_pdf(bundle, pdf_path)

    manifest_path = work / "manifest.json"
    manifest_path.write_text(
        json.dumps(bundle.manifest.model_dump(mode="json"), sort_keys=True, default=str)
    )

    readme_path = work / "README.txt"
    readme_path.write_text(_README_BODY)

    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src, arcname in (
            (pdf_path, "report.pdf"),
            (html_path, "report.html"),
            (json_path, "report.json"),
            (manifest_path, "manifest.json"),
            (readme_path, "README.txt"),
        ):
            zf.write(src, arcname=arcname)

    return BundleArtefacts(
        archive_path=dest,
        html_path=html_path,
        json_path=json_path,
        pdf_path=pdf_path,
        manifest_path=manifest_path,
        readme_path=readme_path,
    )
