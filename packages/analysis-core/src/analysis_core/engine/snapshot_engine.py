"""Snapshot-replay engine adapter for hermetic unit tests.

Reads pre-recorded engine output from
`tests/fixtures/stockfish/<engine-sha>/<pgn-sha>/<ply>.json` so the
test suite does not require a real Stockfish binary. The snapshot
shape mirrors what `analysis.py` will produce in US1 (T048) so test
fixtures stay one-to-one with the production schema.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SnapshotEngine:
    """Reads recorded engine output from disk; never spawns a binary."""

    def __init__(self, root: Path, engine_sha: str) -> None:
        self._root = root
        self._engine_sha = engine_sha

    def analyse(self, pgn_sha: str, ply: int) -> dict[str, Any]:
        """Return the recorded analysis snapshot for one position."""
        path = self._root / self._engine_sha / pgn_sha / f"{ply}.json"
        if not path.is_file():
            raise FileNotFoundError(
                f"no snapshot for engine={self._engine_sha} pgn={pgn_sha} ply={ply}"
            )
        loaded: dict[str, Any] = json.loads(path.read_text())
        return loaded

    def has_snapshot(self, pgn_sha: str, ply: int) -> bool:
        path = self._root / self._engine_sha / pgn_sha / f"{ply}.json"
        return path.is_file()
