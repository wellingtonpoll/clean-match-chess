"""AuditReport + AuditFinding (T019)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class AuditName(StrEnum):
    PALETTE = "palette"
    TYPOGRAPHY = "typography"
    MOTION = "motion"
    LEXICAL = "lexical"


class Severity(StrEnum):
    BLOCK = "block"
    WARN = "warn"


class AuditStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class AuditFinding:
    severity: Severity
    rule: str
    location: str
    expected: str
    actual: str
    message: str


@dataclass(frozen=True, slots=True)
class TrackResult:
    name: str
    status: AuditStatus
    findings: tuple[AuditFinding, ...] = ()


@dataclass(frozen=True, slots=True)
class AuditReport:
    audit_name: AuditName
    artefact: str
    started_at: datetime
    finished_at: datetime
    status: AuditStatus
    findings: tuple[AuditFinding, ...] = ()
    tracks: dict[str, TrackResult] = field(default_factory=dict)
    tool_version: str = "0.1.0"

    def to_json(self) -> str:
        return json.dumps(self._serialize(), sort_keys=True, default=str)

    def _serialize(self) -> dict[str, Any]:
        return {
            "audit_name": self.audit_name.value,
            "artefact": self.artefact,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "status": self.status.value,
            "findings": [asdict(f) for f in self.findings],
            "tracks": {
                name: {
                    "name": tr.name,
                    "status": tr.status.value,
                    "findings": [asdict(f) for f in tr.findings],
                }
                for name, tr in self.tracks.items()
            },
            "tool_version": self.tool_version,
        }


def empty_report(audit_name: AuditName, artefact: str) -> AuditReport:
    now = datetime.now(UTC)
    return AuditReport(
        audit_name=audit_name,
        artefact=artefact,
        started_at=now,
        finished_at=now,
        status=AuditStatus.PASS,
        findings=(),
    )


__all__ = [
    "AuditFinding",
    "AuditName",
    "AuditReport",
    "AuditStatus",
    "Severity",
    "TrackResult",
    "empty_report",
]
