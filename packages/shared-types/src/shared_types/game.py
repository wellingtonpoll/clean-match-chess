"""Game / Position / Move / Player Pydantic schemas (data-model.md sections 1 to 6)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PlayerColor(StrEnum):
    WHITE = "white"
    BLACK = "black"


class Result(StrEnum):
    WHITE_WINS = "1-0"
    BLACK_WINS = "0-1"
    DRAW = "1/2-1/2"
    UNKNOWN = "*"


class TimeControlCategory(StrEnum):
    BULLET = "bullet"
    BLITZ = "blitz"
    RAPID = "rapid"
    CLASSICAL = "classical"
    CORRESPONDENCE = "correspondence"


class MoveClassification(StrEnum):
    BOOK = "book"
    BRILLIANT = "brilliant"
    BEST = "best"
    EXCELLENT = "excellent"
    GOOD = "good"
    INACCURACY = "inaccuracy"
    MISTAKE = "mistake"
    BLUNDER = "blunder"
    FORCED = "forced"
    ONLY_MOVE = "only_move"


class TimeControl(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    raw: str = Field(description="Original PGN TimeControl tag.")
    category: TimeControlCategory
    base_seconds: int | None = Field(default=None, ge=0)
    increment_seconds: int | None = Field(default=None, ge=0)


class PlayerRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    color: PlayerColor
    username: str | None = None
    display_name: str | None = None
    rating: int | None = Field(default=None, ge=0)
    subject: bool = False


class ComplexityScore(BaseModel):
    """Per-position complexity decomposition (FR-006)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    branching_factor: float = Field(ge=0.0)
    eval_volatility: float = Field(ge=0.0)
    tactical_density: float = Field(ge=0.0)
    move_ambiguity: float = Field(ge=0.0)
    composite: float = Field(ge=0.0, le=1.0)


class CandidateMove(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    san: str
    uci: str
    eval_cp: int | None = None
    mate_in: int | None = None
    pv: tuple[str, ...] = ()
    rank: int = Field(ge=1)


class Position(BaseModel):
    """Board state at a given ply with engine analysis attached."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ply: int = Field(ge=0)
    fen: str
    side_to_move: PlayerColor
    eval_cp: int | None = None
    mate_in: int | None = None
    top_moves: tuple[CandidateMove, ...] = ()
    complexity: ComplexityScore | None = None
    is_critical: bool = False
    is_only_move: bool = False
    is_book: bool = False


class Move(BaseModel):
    """A move actually played in the game."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ply: int = Field(ge=0)
    san: str
    uci: str
    played_by: PlayerColor
    time_spent_ms: int | None = Field(default=None, ge=0)
    eval_delta_cp: int = 0
    classification: MoveClassification
    signal_contributions: tuple[_SignalContributionRef, ...] = ()


class _SignalContributionRef(BaseModel):
    """Lightweight ref to a `signal.SignalContribution` (forward-decl).

    Stored as a plain mapping to avoid circular import; the actual rich
    type lives in `shared_types.signal`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    signal_name: str
    signal_version: str
    value: float
    weight: float
    rationale: str


Move.model_rebuild()


class Game(BaseModel):
    """A parsed chess game (data-model.md §1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(description="UUID4 hex.")
    pgn_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: str = Field(description="'file' | 'chesscom' | 'paste'.")
    headers: dict[str, str] = Field(default_factory=dict)
    players: tuple[PlayerRef, PlayerRef]
    result: Result
    time_control: TimeControl
    eco: str | None = None
    ply_count: int = Field(ge=0)
    variant: str = "standard"
    moves: tuple[Move, ...] = ()

    def model_post_init(self, __context: object) -> None:
        if self.variant != "standard":
            raise ValueError(
                f"variant {self.variant!r} unsupported in MVP; only 'standard' is allowed"
            )
        if len(self.moves) != self.ply_count:
            raise ValueError(f"ply_count={self.ply_count} but moves has {len(self.moves)} entries")
