"""chess.com client contract (T061 + T062)."""

from __future__ import annotations

import pytest
from analysis_core.ingest.chesscom_client import (
    BACKOFF_SCHEDULE_SECONDS,
    ChesscomClient,
    ChesscomError,
)

_MIN_PGN = (
    '[Event "Live Chess"]\n[Site "Chess.com"]\n[White "alice"]\n[Black "bob"]\n'
    '[Result "1-0"]\n[TimeControl "600"]\n\n1. e4 e5 *\n'
)


def _archives_url() -> str:
    return "https://api.chess.com/pub/player/alice/games/archives"


def _archive_url(year: int, month: int) -> str:
    return f"https://api.chess.com/pub/player/alice/games/{year}/{month:02d}"


@pytest.fixture
def sleep_recorder():
    calls: list[float] = []

    def _record(n: float) -> None:
        calls.append(n)

    return calls, _record


def test_fetch_recent_games_happy_path(httpx_mock, sleep_recorder) -> None:
    calls, sleep = sleep_recorder
    httpx_mock.add_response(
        method="GET",
        url=_archives_url(),
        json={"archives": [_archive_url(2026, 4), _archive_url(2026, 5)]},
    )
    httpx_mock.add_response(
        method="GET",
        url=_archive_url(2026, 5),
        json={
            "games": [
                {"pgn": _MIN_PGN, "time_class": "rapid", "end_time": 200},
                {"pgn": _MIN_PGN, "time_class": "blitz", "end_time": 100},
            ]
        },
    )

    with ChesscomClient(sleep=sleep) as client:
        games = client.fetch_recent_games("alice", count=2)

    assert len(games) == 2
    assert games[0].end_time_unix == 200
    assert games[1].end_time_unix == 100
    assert calls == []


def test_fetch_recent_games_filters_by_time_control(httpx_mock, sleep_recorder) -> None:
    _, sleep = sleep_recorder
    httpx_mock.add_response(
        method="GET",
        url=_archives_url(),
        json={"archives": [_archive_url(2026, 5)]},
    )
    httpx_mock.add_response(
        method="GET",
        url=_archive_url(2026, 5),
        json={
            "games": [
                {"pgn": _MIN_PGN, "time_class": "rapid", "end_time": 200},
                {"pgn": _MIN_PGN, "time_class": "blitz", "end_time": 100},
            ]
        },
    )
    with ChesscomClient(sleep=sleep) as client:
        games = client.fetch_recent_games("alice", count=10, time_controls=("blitz",))
    assert len(games) == 1
    assert games[0].time_control_category == "blitz"


def test_fewer_games_than_requested_returned(httpx_mock, sleep_recorder) -> None:
    _, sleep = sleep_recorder
    httpx_mock.add_response(
        method="GET",
        url=_archives_url(),
        json={"archives": [_archive_url(2026, 5)]},
    )
    httpx_mock.add_response(
        method="GET",
        url=_archive_url(2026, 5),
        json={"games": [{"pgn": _MIN_PGN, "time_class": "rapid", "end_time": 200}]},
    )
    with ChesscomClient(sleep=sleep) as client:
        games = client.fetch_recent_games("alice", count=50)
    assert len(games) == 1


def test_429_triggers_backoff_and_retry(httpx_mock, sleep_recorder) -> None:
    calls, sleep = sleep_recorder
    httpx_mock.add_response(
        method="GET",
        url=_archives_url(),
        status_code=429,
    )
    httpx_mock.add_response(
        method="GET",
        url=_archives_url(),
        json={"archives": [_archive_url(2026, 5)]},
    )
    httpx_mock.add_response(
        method="GET",
        url=_archive_url(2026, 5),
        json={"games": [{"pgn": _MIN_PGN, "time_class": "rapid", "end_time": 200}]},
    )
    with ChesscomClient(sleep=sleep) as client:
        games = client.fetch_recent_games("alice", count=1)
    assert len(games) == 1
    assert calls and calls[0] == BACKOFF_SCHEDULE_SECONDS[0]


def test_429_exhausts_retries_then_raises(httpx_mock, sleep_recorder) -> None:
    from analysis_core.ingest.chesscom_client import MAX_RETRIES

    _, sleep = sleep_recorder
    for _ in range(MAX_RETRIES + 1):
        httpx_mock.add_response(method="GET", url=_archives_url(), status_code=429)
    with ChesscomClient(sleep=sleep) as client, pytest.raises(ChesscomError):
        client.fetch_recent_games("alice", count=1)


def test_username_required(sleep_recorder) -> None:
    _, sleep = sleep_recorder
    with pytest.raises(ChesscomError, match="username"):
        ChesscomClient(sleep=sleep).fetch_recent_games("", count=1)


def test_count_must_be_positive(sleep_recorder) -> None:
    _, sleep = sleep_recorder
    with pytest.raises(ChesscomError, match="count"):
        ChesscomClient(sleep=sleep).fetch_recent_games("alice", count=0)


def test_4xx_other_than_429_raises_immediately(httpx_mock, sleep_recorder) -> None:
    _, sleep = sleep_recorder
    httpx_mock.add_response(method="GET", url=_archives_url(), status_code=404)
    with ChesscomClient(sleep=sleep) as client, pytest.raises(ChesscomError, match="404"):
        client.fetch_recent_games("alice", count=1)
