"""chess.com Public API client (FR-002).

Reads recent public games for a username from the unauthenticated
`/pub/player/{username}/games/archives` endpoint. Polite defaults +
exponential backoff on 429/5xx with a max 3 retries (research §5).
The client returns raw PGN strings, ordered most-recent-first, with
an optional time-control filter applied before return.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Final

import httpx

API_BASE_URL: Final[str] = "https://api.chess.com"
DEFAULT_USER_AGENT: Final[str] = "cleanmatch/0.1.0 (https://example.invalid)"
MAX_RETRIES: Final[int] = 3
BACKOFF_SCHEDULE_SECONDS: Final[tuple[int, ...]] = (1, 2, 4, 8, 16)


class ChesscomError(RuntimeError):
    """Raised when chess.com cannot be reached or returns an unrecoverable error."""


@dataclass(frozen=True, slots=True)
class FetchedGame:
    """One PGN string plus the chess.com metadata used to filter / order it."""

    pgn: str
    time_control_category: str  # "bullet" | "blitz" | "rapid" | "classical" | "correspondence"
    end_time_unix: int


class ChesscomClient:
    """Synchronous chess.com Public API client."""

    def __init__(
        self,
        *,
        base_url: str = API_BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        sleep: object = time.sleep,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url
        self._sleep = sleep
        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            self._client = httpx.Client(
                base_url=base_url,
                headers={"User-Agent": user_agent, "Accept": "application/json"},
                timeout=httpx.Timeout(15.0),
            )
            self._owns_client = True

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> ChesscomClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def fetch_recent_games(
        self,
        username: str,
        *,
        count: int,
        time_controls: tuple[str, ...] | None = None,
    ) -> list[FetchedGame]:
        """Return up to `count` most-recent public games, newest first."""
        if not username:
            raise ChesscomError("username is required")
        if count < 1:
            raise ChesscomError(f"count must be >= 1; got {count}")

        archives = self._fetch_archives(username)
        out: list[FetchedGame] = []
        for archive_url in reversed(archives):
            month_games = self._fetch_archive(archive_url)
            month_games.sort(key=lambda g: g.end_time_unix, reverse=True)
            for g in month_games:
                if time_controls and g.time_control_category not in time_controls:
                    continue
                out.append(g)
                if len(out) >= count:
                    return out
        return out

    def get_player_profile(self, username: str) -> dict[str, object] | None:
        """Return the `/pub/player/{username}` JSON payload, or None on 404.

        Feature 013: the `status` field of this payload reveals fair-play
        bans. Used by `is_fair_play_banned()` to build a labeled corpus
        crawler. Other fields (player_id, followers, country, last_online,
        league) are kept verbatim for caller use.

        chess.com's URL routing is case-insensitive but redirects via 301
        from any non-canonical form to all-lowercase. Lowercase before the
        request so we never hit the redirect (httpx doesn't auto-follow by
        default + the redirect adds a wasted API call).

        404 (account does not exist) returns None — distinct from a transient
        upstream error, which still raises `ChesscomError`.
        """
        if not username:
            raise ValueError("username must be non-empty")
        url = f"/pub/player/{username.lower()}"
        # Inline HTTP call so we can distinguish 404 cleanly. Reuses the
        # same retry / backoff schedule as `_get_json` for 429 / 5xx.
        for attempt, backoff in enumerate(BACKOFF_SCHEDULE_SECONDS):
            response = self._client.get(url)
            if response.status_code == httpx.codes.OK:
                data = response.json()
                if not isinstance(data, dict):
                    raise ChesscomError(f"expected JSON object from {url}")
                return data
            if response.status_code == httpx.codes.NOT_FOUND:
                return None
            if response.status_code in {429, 500, 502, 503, 504}:
                if attempt >= MAX_RETRIES:
                    raise ChesscomError(
                        f"chess.com returned {response.status_code} for {url} "
                        f"after {attempt} retries"
                    )
                self._sleep(backoff)  # type: ignore[operator]
                continue
            raise ChesscomError(f"chess.com returned {response.status_code} for {url}")
        raise ChesscomError(f"exhausted retries for {url}")

    def is_fair_play_banned(self, username: str) -> bool | None:
        """True iff `/pub/player/{username}` `status` starts with `closed:fair_play`.

        Returns None when the account doesn't exist (404). Callers in the
        crawler treat None and False the same — only True triggers PGN
        ingest.
        """
        profile = self.get_player_profile(username)
        if profile is None:
            return None
        status = profile.get("status")
        if not isinstance(status, str):
            return False
        return status.startswith("closed:fair_play")

    def _fetch_archives(self, username: str) -> list[str]:
        # Lowercase username — chess.com 301-redirects non-canonical case.
        url = f"/pub/player/{username.lower()}/games/archives"
        payload = self._get_json(url)
        archives_raw = payload.get("archives")
        if not isinstance(archives_raw, list):
            raise ChesscomError(f"unexpected archives payload for {username!r}")
        return [str(a) for a in archives_raw]

    def _fetch_archive(self, archive_url: str) -> list[FetchedGame]:
        url = _strip_base_url(archive_url, self._base_url)
        payload = self._get_json(url)
        games_raw = payload.get("games")
        if not isinstance(games_raw, list):
            return []
        return list(_parse_games(games_raw))

    def _get_json(self, url: str) -> dict[str, object]:
        for attempt, backoff in enumerate(BACKOFF_SCHEDULE_SECONDS):
            response = self._client.get(url)
            if response.status_code == httpx.codes.OK:
                data = response.json()
                if isinstance(data, dict):
                    return data
                raise ChesscomError(f"expected JSON object from {url}")
            if response.status_code in {429, 500, 502, 503, 504}:
                if attempt >= MAX_RETRIES:
                    raise ChesscomError(
                        f"chess.com returned {response.status_code} for {url} "
                        f"after {attempt} retries"
                    )
                self._sleep(backoff)  # type: ignore[operator]
                continue
            raise ChesscomError(f"chess.com returned {response.status_code} for {url}")
        raise ChesscomError(f"exhausted retries for {url}")


def _strip_base_url(absolute: str, base: str) -> str:
    return absolute[len(base) :] if absolute.startswith(base) else absolute


def _parse_games(raw: list[object]) -> Iterator[FetchedGame]:
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        pgn = entry.get("pgn")
        if not isinstance(pgn, str) or not pgn.strip():
            continue
        category = str(entry.get("time_class", "rapid"))
        end_time_raw = entry.get("end_time", 0)
        try:
            end_time = int(end_time_raw)
        except (TypeError, ValueError):
            end_time = 0
        yield FetchedGame(pgn=pgn, time_control_category=category, end_time_unix=end_time)
