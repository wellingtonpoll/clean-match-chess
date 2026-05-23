"""Game model invariants."""

from __future__ import annotations

import pytest
from shared_types.game import (
    Game,
    PlayerColor,
    PlayerRef,
    Result,
    TimeControl,
    TimeControlCategory,
)


def _stub_time_control() -> TimeControl:
    return TimeControl(
        raw="600+0", category=TimeControlCategory.RAPID, base_seconds=600, increment_seconds=0
    )


def _stub_players() -> tuple[PlayerRef, PlayerRef]:
    return (
        PlayerRef(color=PlayerColor.WHITE, username="alice", subject=True),
        PlayerRef(color=PlayerColor.BLACK, username="bob"),
    )


def test_game_variant_must_be_standard() -> None:
    with pytest.raises(ValueError, match="variant"):
        Game(
            id="abc",
            pgn_sha256="0" * 64,
            source="file",
            players=_stub_players(),
            result=Result.WHITE_WINS,
            time_control=_stub_time_control(),
            ply_count=0,
            variant="chess960",
        )


def test_game_ply_count_must_match_moves_length() -> None:
    with pytest.raises(ValueError, match="ply_count"):
        Game(
            id="abc",
            pgn_sha256="0" * 64,
            source="file",
            players=_stub_players(),
            result=Result.WHITE_WINS,
            time_control=_stub_time_control(),
            ply_count=5,
            moves=(),
        )


def test_game_pgn_sha256_must_be_lowercase_hex() -> None:
    with pytest.raises(ValueError):
        Game(
            id="abc",
            pgn_sha256="NOTHEX" * 11,
            source="file",
            players=_stub_players(),
            result=Result.WHITE_WINS,
            time_control=_stub_time_control(),
            ply_count=0,
        )
