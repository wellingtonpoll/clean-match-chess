"""Narrative builder (T088)."""

from __future__ import annotations

from datetime import UTC, datetime

from report_engine.lexical_audit import audit_text
from report_engine.narrative import build_narrative
from shared_types.audit_run import AuditRun, EngineFingerprint, RunMode, RunStatus
from shared_types.game import PlayerColor, PlayerRef
from shared_types.score import RiskLevel, SuspicionScore
from shared_types.signal import HeuristicVersion


def _run() -> AuditRun:
    return AuditRun(
        id="x" * 32,
        created_at=datetime.now(UTC),
        mode=RunMode.SINGLE_GAME,
        subject=PlayerRef(color=PlayerColor.WHITE, username="alice", subject=True),
        engine=EngineFingerprint(
            name="Stockfish",
            version="static",
            binary_sha256="0" * 64,
            uci_options={"Threads": 1},
        ),
        heuristic_set=(
            HeuristicVersion(
                name="engine-correlation",
                version="0.1.0",
                git_sha="0000000",
                owner="cleanmatch",
                changelog_path="x",
            ),
        ),
        score=SuspicionScore(score=0.1, risk_level=RiskLevel.LOW, confidence_interval=(0.05, 0.2)),
        status=RunStatus.COMPLETE,
    )


def test_low_risk_summary_en_passes_lexical_audit() -> None:
    n = build_narrative(_run(), _run().score, (), language="en")
    assert audit_text(n.summary_paragraph) == []
    assert "LOW" in n.summary_paragraph
    assert n.flagged_segments == ()


def test_low_risk_summary_pt_passes_lexical_audit() -> None:
    n = build_narrative(_run(), _run().score, (), language="pt")
    assert audit_text(n.summary_paragraph) == []
    assert "BAIXO" in n.summary_paragraph


def test_high_risk_summary_en_does_not_use_accusatory_language() -> None:
    score = SuspicionScore(
        score=0.85,
        risk_level=RiskLevel.HIGH,
        confidence_interval=(0.75, 0.92),
        dominant_signals=("engine-correlation/weighted",),
    )
    n = build_narrative(_run(), score, (), language="en")
    assert audit_text(n.summary_paragraph) == []
    assert "HIGH" in n.summary_paragraph
    assert "not an accusation" in n.summary_paragraph
