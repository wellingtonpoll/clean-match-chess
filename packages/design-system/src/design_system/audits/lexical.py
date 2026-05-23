"""Lexical audit (T040-T042).

Per-language regex scan over rendered text. Feature 001's
`report_engine.lexical_audit` is a sibling implementation; this module
is the design-system-owned canonical scanner that feature-002 audits
will route through.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from design_system.audits.report import (
    AuditFinding,
    AuditName,
    AuditReport,
    AuditStatus,
    Severity,
)
from design_system.lexicon.lookup import (
    ForbiddenTermsFile,
    MatchMode,
    load_forbidden_terms,
)


def audit_text(
    text: str,
    *,
    languages: tuple[str, ...] = ("en", "pt"),
    root: Path | None = None,
    artefact_label: str = "<text>",
) -> AuditReport:
    started = datetime.now(UTC)
    findings: list[AuditFinding] = []
    for lang in languages:
        ft = load_forbidden_terms(lang, root=root)
        findings.extend(_scan(text, ft, artefact_label))
    finished = datetime.now(UTC)
    status = AuditStatus.PASS if not findings else AuditStatus.FAIL
    return AuditReport(
        audit_name=AuditName.LEXICAL,
        artefact=artefact_label,
        started_at=started,
        finished_at=finished,
        status=status,
        findings=tuple(findings),
    )


def audit_file(
    path: Path,
    *,
    languages: tuple[str, ...] = ("en", "pt"),
    root: Path | None = None,
) -> AuditReport:
    return audit_text(
        path.read_text(),
        languages=languages,
        root=root,
        artefact_label=str(path),
    )


def _scan(text: str, ft: ForbiddenTermsFile, artefact_label: str) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for entry in ft.terms:
        if entry.match_mode is MatchMode.WORD_BOUNDARY:
            pattern = re.compile(r"\b" + re.escape(entry.term) + r"\b", re.IGNORECASE)
        else:
            pattern = re.compile(re.escape(entry.term), re.IGNORECASE)
        for match in pattern.finditer(text):
            findings.append(
                AuditFinding(
                    severity=Severity.BLOCK,
                    rule="forbidden_term",
                    location=f"{artefact_label}:{_line_of(text, match.start())}",
                    expected="zero matches",
                    actual=match.group(0),
                    message=(
                        f"{ft.language} forbidden term {entry.term!r} matched at {match.start()}"
                    ),
                )
            )
    return findings


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


__all__ = ["audit_file", "audit_text"]
