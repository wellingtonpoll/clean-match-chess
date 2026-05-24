"""AuditRun / EngineFingerprint / AccountProfile schemas (data-model.md sections 10 to 12)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from shared_types.game import PlayerRef
from shared_types.report import ReproducibilityManifest
from shared_types.score import SuspicionScore
from shared_types.signal import HeuristicVersion


class RunMode(StrEnum):
    SINGLE_GAME = "single_game"
    USERNAME_BATCH = "username_batch"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    PARTIAL = "partial"
    ERROR = "error"


class RunErrorCode(StrEnum):
    USER_ERROR = "user_error"
    UPSTREAM_ERROR = "upstream_error"
    INTERNAL_ERROR = "internal_error"


class RunError(BaseModel):
    """Structured failure record mapping to CLI exit codes 1 / 2 / 3."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: RunErrorCode
    category: str = Field(min_length=1)
    message: str = Field(min_length=1)
    next_step: str | None = None


class EngineFingerprint(BaseModel):
    """Identity of the chess engine used for a run (FR-015)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str
    binary_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    uci_options: dict[str, str | int | bool] = Field(default_factory=dict)
    nnue_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class CrossGamePattern(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    support: float = Field(ge=0.0, le=1.0)
    evidence_runs: tuple[str, ...] = ()


class AccountProfile(BaseModel):
    """Aggregated profile for a username batch audit."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    username: str
    platform: str = Field(default="chesscom", description="Only 'chesscom' supported in MVP.")
    games_audited: int = Field(ge=0)
    per_game_scores: tuple[SuspicionScore, ...] = ()
    aggregate_score: SuspicionScore
    cross_game_patterns: tuple[CrossGamePattern, ...] = ()


class AuditRun(BaseModel):
    """Top-level audit-run record persisted under ~/.cleanmatch/runs/<id>/.

    ``manifest`` (feature 005 FR-003 / US4) is the reproducibility provenance
    attached in-band by the pipeline. ``None`` for legacy / cached AuditRun
    objects that pre-date the field; populated for any audit produced by the
    v2.0.0 pipeline.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    id: str = Field(description="UUID4 hex.")
    created_at: datetime
    mode: RunMode
    subject: PlayerRef
    games: tuple[str, ...] = ()
    engine: EngineFingerprint
    heuristic_set: tuple[HeuristicVersion, ...]
    score: SuspicionScore | None = None
    account_profile: AccountProfile | None = None
    status: RunStatus = RunStatus.PENDING
    error: RunError | None = None
    manifest: ReproducibilityManifest | None = None

    def model_post_init(self, __context: object) -> None:
        if self.mode is RunMode.SINGLE_GAME and self.account_profile is not None:
            raise ValueError("single_game runs must not carry an account_profile")
        if self.mode is RunMode.USERNAME_BATCH and self.score is not None:
            raise ValueError("username_batch runs aggregate via account_profile, not score")
