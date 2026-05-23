"""Lexicon + forbidden-terms loaders (T014).

Sources of truth:
- Analytical lexicon: per-language JSON files under
  `packages/design-system/src/design_system/lexicon/entries_<lang>.json`.
- Forbidden terms: TSV files at the cross-feature path
  `tests/fixtures/forbidden-terms/<lang>.txt` owned by feature 001.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

LEXICON_ROOT: Final[Path] = Path(__file__).resolve().parent
FORBIDDEN_TERMS_ROOT: Final[Path] = (
    Path(__file__).resolve().parents[5] / "tests" / "fixtures" / "forbidden-terms"
)


class ForbiddenCategory(StrEnum):
    ACCUSATION = "accusation"
    VERDICT = "verdict"
    SLUR = "slur"


class MatchMode(StrEnum):
    WORD_BOUNDARY = "word_boundary"
    SUBSTRING = "substring"


@dataclass(frozen=True, slots=True)
class LexiconEntry:
    term: str
    definition: str
    context: str
    alternatives_preferred: tuple[str, ...] = ()
    alternatives_forbidden: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Lexicon:
    language: str
    version: str
    entries: tuple[LexiconEntry, ...]


@dataclass(frozen=True, slots=True)
class ForbiddenTerm:
    term: str
    category: ForbiddenCategory
    match_mode: MatchMode


@dataclass(frozen=True, slots=True)
class ForbiddenTermsFile:
    language: str
    version: str
    terms: tuple[ForbiddenTerm, ...]


class LexiconValidationError(ValueError):
    """Raised when a lexicon or forbidden-terms file is malformed."""


def load_lexicon(language: str, root: Path | None = None) -> Lexicon:
    root = root or LEXICON_ROOT
    path = root / f"entries_{language}.json"
    if not path.is_file():
        raise FileNotFoundError(f"lexicon file not found: {path}")
    payload = json.loads(path.read_text())
    entries = tuple(
        LexiconEntry(
            term=e["term"],
            definition=e["definition"],
            context=e.get("context", ""),
            alternatives_preferred=tuple(e.get("alternatives_preferred", ())),
            alternatives_forbidden=tuple(e.get("alternatives_forbidden", ())),
        )
        for e in payload.get("entries", [])
    )
    return Lexicon(
        language=payload.get("language", language),
        version=payload.get("version", "0.1.0"),
        entries=entries,
    )


def load_forbidden_terms(language: str, root: Path | None = None) -> ForbiddenTermsFile:
    root = root or FORBIDDEN_TERMS_ROOT
    path = root / f"{language}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"forbidden-terms file not found: {path}")

    raw = path.read_text()
    version = _parse_version(raw)
    entries: list[ForbiddenTerm] = []
    for line_no, line in enumerate(raw.splitlines(), start=1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            raise LexiconValidationError(
                f"{path}:{line_no}: expected 3 TSV columns, got {len(parts)}"
            )
        term, category_raw, mode_raw = parts
        try:
            category = ForbiddenCategory(category_raw.strip())
            mode = MatchMode(mode_raw.strip())
        except ValueError as exc:
            raise LexiconValidationError(
                f"{path}:{line_no}: invalid category or match_mode ({exc})"
            ) from exc
        entries.append(ForbiddenTerm(term=term.strip(), category=category, match_mode=mode))

    return ForbiddenTermsFile(language=language, version=version, terms=tuple(entries))


def forbidden_alternatives_resolve(
    entry: LexiconEntry,
    forbidden_terms: ForbiddenTermsFile,
) -> bool:
    """True iff every term in `entry.alternatives_forbidden` appears in the file."""
    universe = {t.term.lower() for t in forbidden_terms.terms}
    return all(alt.lower() in universe for alt in entry.alternatives_forbidden)


def _parse_version(raw: str) -> str:
    for line in raw.splitlines():
        if line.strip().startswith("# version:"):
            return line.split(":", 1)[1].strip()
    return "0.0.0"
