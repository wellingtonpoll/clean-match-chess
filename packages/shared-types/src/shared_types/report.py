"""Report / Manifest schemas (data-model.md sections 13 to 14).

The ReproducibilityManifest carries the `design_system_version` field
declared by feature 002-design-system FR-016. The field is required
for newly produced manifests; legacy manifests without it are accepted
by consumers under a documented warn-only rule.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from shared_types.signal import HeuristicVersion, Segment


class ReportFormat(StrEnum):
    PDF = "pdf"
    HTML = "html"
    JSON = "json"


class ReportLanguage(StrEnum):
    EN = "en"
    PT = "pt"


class HostInfo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    os: str
    arch: str
    cpu_model: str
    ram_bytes: int = Field(ge=0)


class ReproducibilityManifest(BaseModel):
    """Embedded in every rendered report (FR-015)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    engine_name: str
    engine_version: str
    engine_binary_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    engine_uci_options: dict[str, str | int | bool] = Field(default_factory=dict)
    heuristics: tuple[HeuristicVersion, ...]
    analysis_core_version: str
    report_engine_version: str
    python_chess_version: str
    opening_book_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_pgn_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    started_at: datetime
    host: HostInfo
    design_system_version: str = Field(
        pattern=r"^\d+\.\d+\.\d+(?:[-+].+)?$",
        description="Forensic-analytics design-system semver (feature 002 FR-016).",
    )


class FlaggedSegment(BaseModel):
    """A segment that the narrative calls out as suspicious."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    segment: Segment
    headline: str = Field(min_length=1)
    evidence: tuple[str, ...] = Field(
        min_length=3,
        description="Each flag MUST cite >=1 move, >=1 signal, and >=1 principle.",
    )


class Narrative(BaseModel):
    """Human-readable summary attached to a rendered report (FR-012)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    summary_paragraph: str = Field(min_length=1, max_length=2000)
    flagged_segments: tuple[FlaggedSegment, ...] = ()
    forbidden_terms_clean: bool = True


class ReportBundle(BaseModel):
    """A produced report bundle (PDF + HTML + JSON + manifest)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    formats: frozenset[ReportFormat]
    language: ReportLanguage
    narrative: Narrative
    manifest: ReproducibilityManifest
