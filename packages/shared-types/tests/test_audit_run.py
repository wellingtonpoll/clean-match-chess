"""AuditRun mode/payload invariants."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from shared_types.audit_run import (
    AccountProfile,
    AuditRun,
    EngineFingerprint,
    RunMode,
)
from shared_types.game import PlayerColor, PlayerRef
from shared_types.score import RiskLevel, SuspicionScore
from shared_types.signal import HeuristicVersion


def _engine() -> EngineFingerprint:
    return EngineFingerprint(
        name="Stockfish",
        version="16.1",
        binary_sha256="a" * 64,
        uci_options={"Threads": 1, "Hash": 256, "MultiPV": 5},
    )


def _heuristic() -> HeuristicVersion:
    return HeuristicVersion(
        name="engine-correlation",
        version="0.1.0",
        git_sha="abc1234",
        owner="cleanmatch",
        changelog_path="packages/heuristics/CHANGELOG.md",
    )


def _score() -> SuspicionScore:
    return SuspicionScore(score=0.1, risk_level=RiskLevel.LOW, confidence_interval=(0.05, 0.2))


def _subject() -> PlayerRef:
    return PlayerRef(color=PlayerColor.WHITE, username="alice", subject=True)


def test_single_game_with_account_profile_rejected() -> None:
    profile = AccountProfile(username="alice", games_audited=1, aggregate_score=_score())
    with pytest.raises(ValueError, match="single_game"):
        AuditRun(
            id="r1",
            created_at=datetime.now(UTC),
            mode=RunMode.SINGLE_GAME,
            subject=_subject(),
            engine=_engine(),
            heuristic_set=(_heuristic(),),
            account_profile=profile,
        )


def test_username_batch_with_score_rejected() -> None:
    with pytest.raises(ValueError, match="username_batch"):
        AuditRun(
            id="r2",
            created_at=datetime.now(UTC),
            mode=RunMode.USERNAME_BATCH,
            subject=_subject(),
            engine=_engine(),
            heuristic_set=(_heuristic(),),
            score=_score(),
        )
