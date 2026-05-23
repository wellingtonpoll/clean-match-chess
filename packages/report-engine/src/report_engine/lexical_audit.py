"""Lexical audit (T081 / T092).

Scans a rendered text artefact against the per-language forbidden-terms
fixture files. Returns a list of findings (empty = pass). Used by the
bundle producer to enforce SC-008 / FR-013 before writing the export
archive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

DEFAULT_FORBIDDEN_TERMS_DIR: Final[Path] = (
    Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "forbidden-terms"
)


@dataclass(frozen=True, slots=True)
class ForbiddenTerm:
    term: str
    category: str
    match_mode: str  # "word_boundary" | "substring"


@dataclass(frozen=True, slots=True)
class LexicalFinding:
    language: str
    term: str
    category: str
    matched_span: str


def load_forbidden_terms(language: str, root: Path | None = None) -> tuple[ForbiddenTerm, ...]:
    root = root or DEFAULT_FORBIDDEN_TERMS_DIR
    path = root / f"{language}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"forbidden-terms file not found: {path}")
    out: list[ForbiddenTerm] = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        term, category, match_mode = parts
        out.append(
            ForbiddenTerm(
                term=term.strip(), category=category.strip(), match_mode=match_mode.strip()
            )
        )
    return tuple(out)


def audit_text(
    text: str,
    *,
    languages: tuple[str, ...] = ("en", "pt"),
    root: Path | None = None,
) -> list[LexicalFinding]:
    findings: list[LexicalFinding] = []
    for lang in languages:
        terms = load_forbidden_terms(lang, root=root)
        for entry in terms:
            for span in _matches(text, entry):
                findings.append(
                    LexicalFinding(
                        language=lang,
                        term=entry.term,
                        category=entry.category,
                        matched_span=span,
                    )
                )
    return findings


def _matches(text: str, entry: ForbiddenTerm) -> list[str]:
    if entry.match_mode == "word_boundary":
        pattern = r"\b" + re.escape(entry.term) + r"\b"
    else:
        pattern = re.escape(entry.term)
    hits = re.findall(pattern, text, flags=re.IGNORECASE)
    return [str(h) for h in hits]


class LexicalAuditError(RuntimeError):
    """Raised when a render produces text with forbidden vocabulary."""

    def __init__(self, findings: list[LexicalFinding]) -> None:
        self.findings = findings
        summary = ", ".join(f"{f.language}:{f.term}" for f in findings[:5])
        super().__init__(f"lexical audit failed with {len(findings)} finding(s): {summary}")
