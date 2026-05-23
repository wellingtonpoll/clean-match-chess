"""PDF report renderer via WeasyPrint (T087).

Writes a PDF to the given path. Determinism is achieved by:
- not embedding a creation timestamp (PDF metadata kept minimal)
- producing the input HTML deterministically (see render_html)

Cross-architecture byte-stability is best-effort; same-architecture
identity is the binding contract per spec FR-017.
"""

from __future__ import annotations

from pathlib import Path

import weasyprint
from shared_types.report import ReportBundle

from report_engine.render_html import render_report_html


def render_report_pdf(bundle: ReportBundle, dest: Path) -> Path:
    html = render_report_html(bundle)
    dest.parent.mkdir(parents=True, exist_ok=True)
    document = weasyprint.HTML(string=html).render()
    document.write_pdf(target=str(dest))
    return dest
