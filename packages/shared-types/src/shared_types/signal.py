"""Signal / Segment / HeuristicVersion schemas (data-model.md sections 7 to 8)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Phase(StrEnum):
    OPENING = "opening"
    MIDDLEGAME = "middlegame"
    TACTICAL = "tactical"
    CONVERSION = "conversion"
    ENDGAME = "endgame"


class Regime(StrEnum):
    HUMAN_LIKE = "human_like"
    MIXED = "mixed"
    ENGINE_LIKE = "engine_like"
    UNDETERMINED = "undetermined"


class HeuristicVersion(BaseModel):
    """Identity card for a single heuristic module (RNF-07 / FR-016)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(pattern=r"^[a-z][a-z0-9-]*$", description="kebab-case.")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+(?:[-+].+)?$")
    git_sha: str = Field(pattern=r"^[0-9a-f]{7,40}$")
    owner: str = Field(min_length=1)
    changelog_path: str = Field(min_length=1)


class SignalContribution(BaseModel):
    """Per-move contribution of a single signal (FR-012)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    signal_name: str
    signal_version: str
    value: float
    weight: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)


class SignalAggregate(BaseModel):
    """Per-segment or per-game aggregate of a signal."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    signal_name: str
    signal_version: str
    mean: float
    weighted_mean: float
    samples: int = Field(ge=0)


class Segment(BaseModel):
    """A phase slice of the game with its own aggregates."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    phase: Phase
    ply_range: tuple[int, int] = Field(description="inclusive start, exclusive end")
    regime: Regime = Regime.UNDETERMINED
    signals: tuple[SignalAggregate, ...] = ()
    score_contribution: float = Field(default=0.0, ge=0.0, le=1.0)

    def model_post_init(self, __context: object) -> None:
        start, end = self.ply_range
        if start < 0 or end < start:
            raise ValueError(f"ply_range invalid: {self.ply_range}")
