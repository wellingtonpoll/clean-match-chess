"""HTML / PDF / JSON report rendering."""

from __future__ import annotations

from report_engine.bundle import BundleArtefacts, write_bundle
from report_engine.lexical_audit import (
    ForbiddenTerm,
    LexicalAuditError,
    LexicalFinding,
    audit_text,
    load_forbidden_terms,
)
from report_engine.narrative import build_narrative
from report_engine.render_html import render_report_html
from report_engine.render_json import render_report_json
from report_engine.render_pdf import render_report_pdf

__all__: list[str] = [
    "BundleArtefacts",
    "ForbiddenTerm",
    "LexicalAuditError",
    "LexicalFinding",
    "audit_text",
    "build_narrative",
    "load_forbidden_terms",
    "render_report_html",
    "render_report_json",
    "render_report_pdf",
    "write_bundle",
]
