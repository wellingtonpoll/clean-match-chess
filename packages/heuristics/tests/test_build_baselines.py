"""Unit tests for `packages/heuristics/scripts/build_baselines.py`.

The real-data path drives Stockfish via subprocess + persists to Postgres;
these tests cover the pure helpers in isolation. End-to-end coverage of
the DB-backed flow lives in `packages/analysis-core/tests/test_baseline_store.py`
plus the real maintainer-machine run (Phase E).

Coverage targets (feature 007 / T005):
  * `_classify_bucket` bucketing boundaries
  * `_passes_filter` filter logic — Elo, TC, ply
  * `reservoir_sample` determinism (same seed → identical sample list)
  * `analyse_game` per-game stat computation (top1, weighted, ACPL)
  * Stub-path output validates against `rating_baselines.schema.json`
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Iterator
from importlib import util as _import_util
from pathlib import Path
from typing import Any

import pytest

# ─── Import the script as a module ────────────────────────────────────────
# The script lives under `packages/heuristics/scripts/` (not on the package
# import path). We load it via importlib for testing — same trick used by
# the rest of the workspace for one-shot maintainer scripts.

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_baselines.py"
_spec = _import_util.spec_from_file_location("build_baselines", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
build_baselines = _import_util.module_from_spec(_spec)
sys.modules["build_baselines"] = build_baselines
_spec.loader.exec_module(build_baselines)


# ─── Static analyzer for engine-free tests ────────────────────────────────


class StaticAnalyzer:
    """Returns canned `PositionEval`s without spawning Stockfish.

    The ``script_fn`` is a callable `(board, ply) -> PositionEval` so tests
    can vary the response per ply. A constant return is the most common
    case and is supported by `constant(...)`.
    """

    def __init__(self, script_fn: Callable[[object, int], build_baselines.PositionEval]) -> None:
        self._script_fn = script_fn
        self.calls: int = 0

    def analyse(self, board: object, ply: int) -> build_baselines.PositionEval:
        self.calls += 1
        return self._script_fn(board, ply)

    @staticmethod
    def constant(pe: build_baselines.PositionEval) -> StaticAnalyzer:
        return StaticAnalyzer(lambda _b, _p: pe)


# ─── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def empty_pos_eval() -> build_baselines.PositionEval:
    """No top moves — equivalent to a terminal position."""
    return build_baselines.PositionEval(
        top_moves=(), complexity_composite=0.0, is_book=False, is_only_move=False
    )


@pytest.fixture
def three_move_eval() -> build_baselines.PositionEval:
    """Three candidates with a 100-cp spread between best and third."""
    return build_baselines.PositionEval(
        top_moves=(
            build_baselines.CandidateEval(uci="e2e4", eval_cp=50),
            build_baselines.CandidateEval(uci="d2d4", eval_cp=30),
            build_baselines.CandidateEval(uci="g1f3", eval_cp=-50),
        ),
        complexity_composite=0.5,
        is_book=False,
        is_only_move=False,
    )


@pytest.fixture
def tiny_pgn() -> str:
    """A 3-ply game from the starting position. UCI moves: e2e4, e7e5, g1f3."""
    return (
        '[Event "Test"]\n'
        '[Site "test"]\n'
        '[Date "2026.05.25"]\n'
        '[Round "?"]\n'
        '[White "A"]\n'
        '[Black "B"]\n'
        '[Result "*"]\n'
        '[WhiteElo "1500"]\n'
        '[BlackElo "1500"]\n'
        '[PlyCount "3"]\n'
        '[Event "Rapid Test"]\n'
        "\n"
        "1. e4 e5 2. Nf3 *\n"
    )


# ─── Bucket classification ────────────────────────────────────────────────


class TestClassifyBucket:
    def test_classifies_low_rating_in_le1200(self) -> None:
        assert build_baselines._classify_bucket(800) == "≤1200"

    def test_classifies_lower_boundary(self) -> None:
        assert build_baselines._classify_bucket(1) == "≤1200"
        assert build_baselines._classify_bucket(1200) == "≤1200"

    def test_classifies_middle_bucket(self) -> None:
        assert build_baselines._classify_bucket(1500) == "1201-1500"
        assert build_baselines._classify_bucket(1501) == "1501-1800"

    def test_classifies_upper_boundary(self) -> None:
        assert build_baselines._classify_bucket(2401) == "2401+"
        assert build_baselines._classify_bucket(3500) == "2401+"

    def test_rejects_below_floor(self) -> None:
        assert build_baselines._classify_bucket(0) is None

    def test_rejects_above_ceiling(self) -> None:
        assert build_baselines._classify_bucket(3501) is None


# ─── Filter logic ─────────────────────────────────────────────────────────


class TestPassesFilter:
    def _headers(self, **overrides: Any) -> dict[str, str]:
        h = {
            "WhiteElo": "1500",
            "BlackElo": "1500",
            "Event": "Rated Rapid game",
            "PlyCount": "40",
        }
        h.update(overrides)
        return h

    def test_accepts_in_window_rapid(self) -> None:
        assert build_baselines._passes_filter(self._headers(), 40) == "1201-1500"

    def test_accepts_classical(self) -> None:
        h = self._headers(Event="Rated Classical game")
        assert build_baselines._passes_filter(h, 40) == "1201-1500"

    def test_rejects_blitz(self) -> None:
        h = self._headers(Event="Rated Blitz game")
        assert build_baselines._passes_filter(h, 40) is None

    def test_rejects_low_elo(self) -> None:
        h = self._headers(WhiteElo="500")
        assert build_baselines._passes_filter(h, 40) is None

    def test_rejects_high_elo(self) -> None:
        h = self._headers(BlackElo="9999")
        assert build_baselines._passes_filter(h, 40) is None

    def test_rejects_short_game(self) -> None:
        assert build_baselines._passes_filter(self._headers(), 10) is None

    def test_rejects_malformed_elo(self) -> None:
        h = self._headers(WhiteElo="abc")
        assert build_baselines._passes_filter(h, 40) is None

    def test_uses_min_for_bucket_key(self) -> None:
        """A 1200 vs 1500 game lands in the ≤1200 bucket (lower of both)."""
        h = self._headers(WhiteElo="1200", BlackElo="1500")
        assert build_baselines._passes_filter(h, 40) == "≤1200"


# ─── Reservoir sampling ───────────────────────────────────────────────────


def _make_stream(n: int, bucket_label: str = "1501-1800") -> Iterator[tuple[dict[str, str], str]]:
    """Synthesise N pseudo-games for the given bucket."""
    rng_seed = 0
    for i in range(n):
        yield (
            {
                "WhiteElo": "1700",
                "BlackElo": "1700",
                "Event": "Rated Rapid game",
                "PlyCount": "40",
            },
            f"PGN#{i}@{bucket_label}@{rng_seed}",
        )


class TestReservoirSample:
    def test_collects_full_bucket_when_stream_exceeds_target(self) -> None:
        result = build_baselines.reservoir_sample(
            _make_stream(500),
            per_bucket_sample=100,
            seed=0,
        )
        assert len(result["1501-1800"]) == 100
        # Other buckets stay empty.
        assert result["≤1200"] == []
        assert result["2401+"] == []

    def test_keeps_all_when_stream_smaller_than_target(self) -> None:
        result = build_baselines.reservoir_sample(
            _make_stream(50),
            per_bucket_sample=100,
            seed=0,
        )
        assert len(result["1501-1800"]) == 50

    def test_determinism_across_runs_with_same_seed(self) -> None:
        a = build_baselines.reservoir_sample(_make_stream(500), per_bucket_sample=20, seed=0)
        b = build_baselines.reservoir_sample(_make_stream(500), per_bucket_sample=20, seed=0)
        assert a == b, "Same seed + same stream MUST produce identical samples"

    def test_different_seed_produces_different_sample(self) -> None:
        a = build_baselines.reservoir_sample(_make_stream(500), per_bucket_sample=20, seed=0)
        b = build_baselines.reservoir_sample(_make_stream(500), per_bucket_sample=20, seed=1)
        # Different seeds — overwhelmingly likely to differ at some index.
        assert a != b


# ─── analyse_game (engine-free via StaticAnalyzer) ───────────────────────


class TestAnalyseGame:
    def test_zero_eligible_plies_returns_zero_stats(
        self, tiny_pgn: str, empty_pos_eval: build_baselines.PositionEval
    ) -> None:
        analyzer = StaticAnalyzer.constant(empty_pos_eval)
        stats = build_baselines.analyse_game(tiny_pgn, analyzer)
        assert stats.eligible_plies == 0
        assert stats.top1_rate == 0.0
        assert stats.acpl == 0.0

    def test_played_move_matches_top1_perfect_score(self, tiny_pgn: str) -> None:
        """All 3 moves match engine top1 — top1_rate=1.0, ACPL=0."""

        # Each ply's "best move" mirrors what the PGN actually plays.
        # tiny_pgn moves: e2e4, e7e5, g1f3. Vary the canned response by ply.
        moves_by_ply = ["e2e4", "e7e5", "g1f3"]

        def script_fn(_board: object, ply: int) -> build_baselines.PositionEval:
            top = build_baselines.CandidateEval(uci=moves_by_ply[ply], eval_cp=50)
            other = build_baselines.CandidateEval(uci="z9z9", eval_cp=0)
            return build_baselines.PositionEval(
                top_moves=(top, other),
                complexity_composite=1.0,
                is_book=False,
                is_only_move=False,
            )

        analyzer = StaticAnalyzer(script_fn)
        stats = build_baselines.analyse_game(tiny_pgn, analyzer)

        assert stats.eligible_plies == 3
        assert stats.top1_rate == 1.0
        assert stats.weighted_rate == 1.0
        assert stats.acpl == 0.0

    def test_played_move_never_in_multipv_applies_penalty(self, tiny_pgn: str) -> None:
        """Played move not in top_moves[] — penalty applied per ply."""

        def script_fn(_board: object, _ply: int) -> build_baselines.PositionEval:
            return build_baselines.PositionEval(
                top_moves=(
                    build_baselines.CandidateEval(uci="a1a8", eval_cp=100),
                    build_baselines.CandidateEval(uci="h1h8", eval_cp=20),
                ),
                complexity_composite=1.0,
                is_book=False,
                is_only_move=False,
            )

        analyzer = StaticAnalyzer(script_fn)
        stats = build_baselines.analyse_game(tiny_pgn, analyzer)

        assert stats.eligible_plies == 3
        assert stats.top1_rate == 0.0
        # Penalty: played_eval = min(20, 100 - 200) = -100; CPL = max(0, 100 - (-100)) = 200
        assert stats.acpl == 200.0

    def test_skips_book_and_only_move_plies(self, tiny_pgn: str) -> None:
        """is_book + is_only_move plies are excluded from eligible_plies."""
        book_eval = build_baselines.PositionEval(
            top_moves=(build_baselines.CandidateEval(uci="e2e4", eval_cp=0),),
            complexity_composite=0.0,
            is_book=True,
            is_only_move=False,
        )
        analyzer = StaticAnalyzer.constant(book_eval)
        stats = build_baselines.analyse_game(tiny_pgn, analyzer)
        assert stats.eligible_plies == 0


# ─── End-to-end build_buckets_real ───────────────────────────────────────
#
# Removed: the DB-backed flow is exercised by
# `packages/analysis-core/tests/test_baseline_store.py` (16 cases) and the
# real maintainer-machine run in Phase E. End-to-end with a fake analyzer
# would require injecting a non-Stockfish worker into the ProcessPool,
# which is more plumbing than it's worth for a maintainer script.


# ─── Output schema validation ────────────────────────────────────────────


class TestOutputSchemaValidation:
    def test_stub_output_validates_against_locked_schema(self, tmp_path: Path) -> None:
        """`--dry-run` JSON must conform to the 004 schema (regression guard)."""
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed in this env")

        schema_path = (
            Path(__file__).resolve().parents[3]
            / "specs"
            / "004-scoring-v2-phase1"
            / "contracts"
            / "rating_baselines.schema.json"
        )
        if not schema_path.exists():
            pytest.skip(f"Schema file not present at {schema_path}")
        schema = json.loads(schema_path.read_text())

        out = tmp_path / "stub.json"
        build_baselines.main(["--dry-run", "--output", str(out)])
        data = json.loads(out.read_text())
        jsonschema.validate(data, schema)  # raises on violation
