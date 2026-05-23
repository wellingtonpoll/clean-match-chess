"""Historical artefact non-regression (T089).

For every fixture under `tests/fixtures/pgn/known-{clean,suspect}/`
asserts that:
1. The PGN file itself contains no forbidden term (lexical audit).
2. The committed adapter CSS artefacts still clear the palette,
   typography, and motion static audits.

Together these constitute the v1.0.0 historical regression gate: when
later versions touch tokens, templates, or wording, this test fails
fast if any pre-existing fixture stops passing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pytest
from design_system.audits.lexical import audit_text
from design_system.audits.motion import audit_static_css
from design_system.audits.palette import audit_generated_css as palette_audit
from design_system.audits.report import AuditStatus
from design_system.audits.typography import audit_generated_css as typography_audit

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]
PGN_KNOWN_CLEAN: Final[Path] = REPO_ROOT / "tests" / "fixtures" / "pgn" / "known-clean"
PGN_KNOWN_SUSPECT: Final[Path] = REPO_ROOT / "tests" / "fixtures" / "pgn" / "known-suspect"

ADAPTERS_ROOT: Final[Path] = (
    Path(__file__).resolve().parents[2] / "adapters" / "weasyprint" / "tokens.css"
)


def _pgn_files() -> list[Path]:
    out: list[Path] = []
    for root in (PGN_KNOWN_CLEAN, PGN_KNOWN_SUSPECT):
        if root.is_dir():
            out.extend(sorted(root.glob("*.pgn")))
    return out


@pytest.mark.parametrize("pgn_path", _pgn_files(), ids=lambda p: p.name)
def test_pgn_fixture_clears_lexical_audit(pgn_path: Path) -> None:
    text = pgn_path.read_text()
    report = audit_text(text, artefact_label=pgn_path.name)
    assert report.status is AuditStatus.PASS, (
        f"{pgn_path.name} lexical regression: {[f.rule for f in report.findings]}"
    )


def test_adapter_css_clears_palette_audit() -> None:
    assert ADAPTERS_ROOT.is_file(), f"missing adapter CSS: {ADAPTERS_ROOT}"
    report = palette_audit(ADAPTERS_ROOT)
    assert report.status is AuditStatus.PASS, (
        f"palette regression: {[f.rule for f in report.findings]}"
    )


def test_adapter_css_clears_typography_audit() -> None:
    report = typography_audit(ADAPTERS_ROOT)
    assert report.status is AuditStatus.PASS, (
        f"typography regression: {[f.rule for f in report.findings]}"
    )


def test_adapter_css_clears_motion_audit() -> None:
    report = audit_static_css(ADAPTERS_ROOT)
    assert report.status is AuditStatus.PASS, (
        f"motion regression: {[f.rule for f in report.findings]}"
    )
