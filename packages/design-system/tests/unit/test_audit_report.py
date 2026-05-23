"""AuditReport + AuditFinding (T018)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from design_system.audits.report import (
    AuditFinding,
    AuditName,
    AuditReport,
    AuditStatus,
    Severity,
    TrackResult,
    empty_report,
)


def test_empty_report_passes() -> None:
    rpt = empty_report(AuditName.LEXICAL, "/tmp/report.pdf")
    assert rpt.status is AuditStatus.PASS
    assert rpt.findings == ()


def test_report_serialises_to_json() -> None:
    finding = AuditFinding(
        severity=Severity.BLOCK,
        rule="forbidden_term",
        location="report.pdf:p1",
        expected="zero matches",
        actual="cheater",
        message="forbidden term found",
    )
    rpt = AuditReport(
        audit_name=AuditName.LEXICAL,
        artefact="report.pdf",
        started_at=datetime(2026, 5, 23, 12, 0, tzinfo=UTC),
        finished_at=datetime(2026, 5, 23, 12, 0, tzinfo=UTC),
        status=AuditStatus.FAIL,
        findings=(finding,),
    )
    payload = json.loads(rpt.to_json())
    assert payload["status"] == "fail"
    assert payload["findings"][0]["rule"] == "forbidden_term"
    assert payload["audit_name"] == "lexical"


def test_report_tracks_serialise() -> None:
    track = TrackResult(name="css", status=AuditStatus.PASS, findings=())
    rpt = AuditReport(
        audit_name=AuditName.PALETTE,
        artefact="report.pdf",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        status=AuditStatus.PASS,
        tracks={"css": track},
    )
    payload = json.loads(rpt.to_json())
    assert payload["tracks"]["css"]["status"] == "pass"
