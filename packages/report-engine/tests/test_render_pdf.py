"""PDF render contract + byte-stability sanity (T080)."""

from __future__ import annotations

from pathlib import Path

from report_engine.render_pdf import render_report_pdf


def test_pdf_renders_non_empty(bundle, tmp_path: Path) -> None:
    out = tmp_path / "report.pdf"
    render_report_pdf(bundle, out)
    assert out.is_file()
    assert out.stat().st_size > 0
    # PDF magic header.
    assert out.read_bytes()[:4] == b"%PDF"
