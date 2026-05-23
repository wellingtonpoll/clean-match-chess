"""PDF reduced-motion invariant (T098 — C4 remediation).

Per FR-014 the PDF surface MUST carry zero motion. The WeasyPrint
adapter's generated CSS is the single source the PDF renderer
consumes — this test asserts no `transition` or `animation`
declarations leak in.

Locked at this level (raw CSS scan) so the test fails the moment
any future drift adds animated CSS, regardless of which token or
which template introduced it.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

WEASYPRINT_CSS: Final[Path] = (
    Path(__file__).resolve().parents[2] / "adapters" / "weasyprint" / "tokens.css"
)

_TRANSITION_PROPERTY_RE: Final[re.Pattern[str]] = re.compile(
    r"\btransition(?:-property|-duration|-timing-function|-delay)?\s*:",
    re.IGNORECASE,
)
_ANIMATION_PROPERTY_RE: Final[re.Pattern[str]] = re.compile(
    r"\banimation(?:-name|-duration|-timing-function|-delay|-iteration-count|-direction|-fill-mode|-play-state)?\s*:",
    re.IGNORECASE,
)
_KEYFRAMES_RE: Final[re.Pattern[str]] = re.compile(r"@(?:-\w+-)?keyframes\b", re.IGNORECASE)


def _read_css() -> str:
    assert WEASYPRINT_CSS.is_file(), f"missing weasyprint CSS: {WEASYPRINT_CSS}"
    return WEASYPRINT_CSS.read_text()


def test_no_transition_declarations() -> None:
    css = _read_css()
    matches = _TRANSITION_PROPERTY_RE.findall(css)
    assert not matches, f"unexpected `transition` declarations in PDF CSS: {matches}"


def test_no_animation_declarations() -> None:
    css = _read_css()
    matches = _ANIMATION_PROPERTY_RE.findall(css)
    assert not matches, f"unexpected `animation` declarations in PDF CSS: {matches}"


def test_no_keyframes_at_rules() -> None:
    css = _read_css()
    matches = _KEYFRAMES_RE.findall(css)
    assert not matches, f"unexpected @keyframes blocks in PDF CSS: {matches}"
