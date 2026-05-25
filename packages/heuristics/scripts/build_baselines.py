"""One-shot maintainer script — derive `rating_baselines.json` from Lichess open database.

Reproducible: pinned dataset month + deterministic seed. Output is the artifact
committed under `packages/heuristics/data/rating_baselines.json`; this script
is NOT invoked at audit time.

Methodology (per spec FR-011 + feature 007 research.md R1-R8):
  1. Stream a Lichess month-export archive (.pgn.zst) via `zstd -d -c` subprocess
     (no full decompress to disk — archive is ~170 GB decompressed).
  2. Filter games: both players Elo in [600, 3500], TC ∈ {RAPID, CLASSICAL},
     ≥ 20 plies.
  3. Bin by min(WhiteElo, BlackElo) into 6 rating buckets.
  4. Reservoir-sample N games per bucket (Algorithm L, seeded RNG).
  5. Run Stockfish depth 12 multipv 3 over sampled positions.
  6. Compute per-bucket: mean+stdev of per-game top1 rate, weighted-top1 rate,
     and ACPL. Add the 7th `rating-unknown` bucket as the elementwise median
     of the 6 rated buckets.
  7. Emit JSON conforming to contracts/rating_baselines.schema.json.

Runtime: ~6 h on a 6-core reference machine. Use --dry-run for code review
without running the engine.

Usage:
    python build_baselines.py --dry-run
    python build_baselines.py \\
        --input-zst ./lichess_db_standard_rated_2026-04.pgn.zst \\
        --stockfish-cmd "podman run --rm -i cleanmatch-stockfish:sf16" \\
        --seed 0 --depth 12 --workers 6 --per-bucket-sample 5000
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import statistics
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

# ─── Constants ────────────────────────────────────────────────────────────

DEFAULT_MONTH = "2026-04"
DEFAULT_SEED = 0
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "rating_baselines.json"
DEFAULT_INPUT_ZST = Path.cwd() / f"lichess_db_standard_rated_{DEFAULT_MONTH}.pgn.zst"
DEFAULT_STOCKFISH_CMD = "podman run --rm -i cleanmatch-stockfish:sf16"
DEFAULT_CHECKPOINT_DIR = Path("/tmp/baselines-007")  # noqa: S108 — maintainer script; predictable path is intentional
DEFAULT_PER_BUCKET_SAMPLE = 5000
DEFAULT_DEPTH = 12
DEFAULT_WORKERS = 6

BUCKET_DEFINITIONS: tuple[tuple[str, int | None, int | None], ...] = (
    ("≤1200", 1, 1200),
    ("1201-1500", 1201, 1500),
    ("1501-1800", 1501, 1800),
    ("1801-2100", 1801, 2100),
    ("2101-2400", 2101, 2400),
    ("2401+", 2401, 3500),
)

# Filter constants per FR-003.
ELIGIBLE_TC_PREFIXES = ("RAPID", "CLASSICAL", "Rapid", "Classical")
MIN_PLY_COUNT = 20
MIN_ELO = 600
MAX_ELO = 3500

# Hand-curated stub values (FR-011 fallback) — derived from anti-cheating literature
# (Regan 2011, public Lichess insights aggregates). Real run replaces with empirical
# percentages. These are documented placeholders, not measured population stats.
STUB_BASELINES: dict[str, dict[str, float]] = {
    "≤1200": dict(top1=0.32, wtop1=0.30, acpl_mean=85.0, acpl_stdev=35.0),
    "1201-1500": dict(top1=0.38, wtop1=0.36, acpl_mean=65.0, acpl_stdev=28.0),
    "1501-1800": dict(top1=0.45, wtop1=0.43, acpl_mean=48.0, acpl_stdev=22.0),
    "1801-2100": dict(top1=0.52, wtop1=0.50, acpl_mean=35.0, acpl_stdev=18.0),
    "2101-2400": dict(top1=0.60, wtop1=0.58, acpl_mean=25.0, acpl_stdev=14.0),
    "2401+": dict(top1=0.68, wtop1=0.66, acpl_mean=18.0, acpl_stdev=10.0),
}

STUB_SAMPLE_SIZE = 0  # Marks the entry as a stub; real run sets to ≥ 1000.

# When a played move is not in the engine's multipv top-K, this is the
# centipawn penalty applied (lower-bound estimate of the loss).
ACPL_OUT_OF_MULTIPV_PENALTY_CP = 200

# ─── Domain types ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CandidateEval:
    """One ranked candidate move from a multipv engine analysis."""

    uci: str
    eval_cp: int


@dataclass(frozen=True)
class PositionEval:
    """Engine analysis of a single position.

    Fields are intentionally narrow — only what `build_baselines.py` consumes.
    Tests inject a `StaticAnalyzer` returning instances of this dataclass with
    canned values, so no real Stockfish is required in CI.
    """

    top_moves: tuple[CandidateEval, ...]
    complexity_composite: float
    is_book: bool
    is_only_move: bool


@dataclass
class GameStats:
    """Per-game aggregated stats. Computed once per sampled game."""

    top1_rate: float = 0.0
    weighted_rate: float = 0.0
    acpl: float = 0.0
    eligible_plies: int = 0


@dataclass
class BucketStats:
    """Per-bucket aggregated stats. Mean + population stdev over games."""

    label: str
    rating_low: int | None
    rating_high: int | None
    games: list[GameStats] = field(default_factory=list)

    def expected_top1(self) -> float:
        return statistics.mean(g.top1_rate for g in self.games) if self.games else 0.0

    def expected_weighted_top1(self) -> float:
        return statistics.mean(g.weighted_rate for g in self.games) if self.games else 0.0

    def expected_acpl_mean(self) -> float:
        return statistics.mean(g.acpl for g in self.games) if self.games else 0.0

    def expected_acpl_stdev(self) -> float:
        # Population stdev (ddof=0) — we measure the entire sampled population.
        if len(self.games) < 2:
            return 0.0
        return statistics.pstdev(g.acpl for g in self.games)

    def sample_size(self) -> int:
        return len(self.games)


# ─── Analyzer Protocol ────────────────────────────────────────────────────


class Analyzer(Protocol):
    """Quack-typed engine wrapper.

    The real implementation calls Stockfish via python-chess UCI; tests inject
    a dummy that returns canned PositionEval instances without spawning a
    subprocess.
    """

    def analyse(self, board: object, ply: int) -> PositionEval: ...


# ─── Stub path (dry-run / Phase 1 fallback) ────────────────────────────────


def build_buckets_stub() -> list[dict[str, object]]:
    """Return the documented stub buckets (FR-011 fallback path).

    Used by `--dry-run` for code review without running the engine.
    """
    buckets: list[dict[str, object]] = []
    for label, low, high in BUCKET_DEFINITIONS:
        s = STUB_BASELINES[label]
        buckets.append(
            {
                "bucket_label": label,
                "rating_low": low,
                "rating_high": high,
                "expected_top1": s["top1"],
                "expected_weighted_top1": s["wtop1"],
                "expected_acpl_mean": s["acpl_mean"],
                "expected_acpl_stdev": s["acpl_stdev"],
                "sample_size": max(STUB_SAMPLE_SIZE, 100),  # schema min
            }
        )
    medians = {
        "top1": sorted(b["top1"] for b in STUB_BASELINES.values())[3],
        "wtop1": sorted(b["wtop1"] for b in STUB_BASELINES.values())[3],
        "acpl_mean": sorted(b["acpl_mean"] for b in STUB_BASELINES.values())[3],
        "acpl_stdev": sorted(b["acpl_stdev"] for b in STUB_BASELINES.values())[3],
    }
    buckets.append(
        {
            "bucket_label": "rating-unknown",
            "rating_low": None,
            "rating_high": None,
            "expected_top1": medians["top1"],
            "expected_weighted_top1": medians["wtop1"],
            "expected_acpl_mean": medians["acpl_mean"],
            "expected_acpl_stdev": medians["acpl_stdev"],
            "sample_size": 100,
        }
    )
    return buckets


# ─── Streaming + filter (Phase 1 of the two-phase build) ──────────────────


def _classify_bucket(elo: int) -> str | None:
    """Return the bucket label whose `[rating_low, rating_high]` covers `elo`."""
    for label, low, high in BUCKET_DEFINITIONS:
        if low is None or high is None:
            continue
        if low <= elo <= high:
            return label
    return None


def _passes_filter(headers: dict[str, str], move_count: int) -> str | None:
    """Apply FR-003 filter and return the bucket label, or None if rejected.

    Rejects:
      - either player's Elo outside [600, 3500]
      - time control not RAPID / CLASSICAL
      - ply count < 20
    """
    try:
        white_elo = int(headers.get("WhiteElo", "0"))
        black_elo = int(headers.get("BlackElo", "0"))
    except ValueError:
        return None
    if not (MIN_ELO <= white_elo <= MAX_ELO and MIN_ELO <= black_elo <= MAX_ELO):
        return None
    if move_count < MIN_PLY_COUNT:
        return None
    event = headers.get("Event", "")
    if not any(tag in event for tag in ELIGIBLE_TC_PREFIXES):
        return None
    return _classify_bucket(min(white_elo, black_elo))


def _open_zst_stream(zst_path: Path) -> subprocess.Popen[bytes]:
    """Spawn `zstd -d -c <path>` and return the running process.

    Caller is responsible for closing stdout + waiting for the process.
    """
    return subprocess.Popen(  # noqa: S603 — trusted local archive path
        ["zstd", "-d", "-c", str(zst_path)],  # noqa: S607 — system-installed zstd
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=1 << 20,
    )


def _stream_pgn_games(zst_path: Path) -> Iterator[tuple[dict[str, str], str]]:
    """Stream `(headers, pgn_text)` pairs from a zst-compressed PGN archive.

    Uses python-chess `chess.pgn.read_game` against an `io.TextIOWrapper`
    fed by `zstd -d -c` subprocess stdout. Yields only the raw PGN text +
    header dict — no parsed board state is retained between iterations.
    """
    import chess.pgn  # lazy: only the maintainer machine needs python-chess

    proc = _open_zst_stream(zst_path)
    assert proc.stdout is not None
    stream = io.TextIOWrapper(proc.stdout, encoding="utf-8", errors="replace")
    try:
        while True:
            offset = stream.tell() if hasattr(stream, "tell") else None
            try:
                game = chess.pgn.read_game(stream)
            except (UnicodeDecodeError, ValueError) as e:
                print(
                    f"[warn] skipping malformed game at offset {offset}: {e}",
                    file=sys.stderr,
                )
                continue
            if game is None:
                break
            headers = dict(game.headers)
            # Materialise the PGN text so we can persist it to a checkpoint
            # later without keeping the parsed Game in memory.
            yield headers, str(game)
    finally:
        stream.close()
        proc.wait()


# ─── Reservoir sampling (Algorithm L, seeded per bucket) ──────────────────


def reservoir_sample(
    stream: Iterator[tuple[dict[str, str], str]],
    *,
    per_bucket_sample: int,
    seed: int,
    progress_every: int = 100_000,
) -> dict[str, list[str]]:
    """Per-bucket reservoir sampling over a stream of (headers, pgn) pairs.

    Algorithm L (Vitter, 1985) — O(n + k log(n/k)) time, O(k) memory per
    bucket. Deterministic for a given seed: an explicit `random.Random(seed)`
    instance per bucket ensures byte-stable output across runs.

    Returns a dict keyed by bucket label, with each value a list of PGN texts
    of length ≤ `per_bucket_sample`.
    """
    buckets: dict[str, list[str]] = {label: [] for label, _, _ in BUCKET_DEFINITIONS}
    rngs: dict[str, random.Random] = {
        label: random.Random((seed << 16) ^ hash(label))  # noqa: S311 — population sampling, not crypto
        for label, _, _ in BUCKET_DEFINITIONS
    }
    seen: dict[str, int] = {label: 0 for label, _, _ in BUCKET_DEFINITIONS}
    total_seen = 0
    accepted = 0
    start = time.time()

    for headers, pgn_text in stream:
        total_seen += 1
        if total_seen % progress_every == 0:
            elapsed = time.time() - start
            rate = total_seen / elapsed if elapsed > 0 else 0
            print(
                f"[stream] scanned {total_seen:,} games | accepted {accepted:,} | "
                f"rate {rate:,.0f}/s | bucket fills: "
                + " ".join(f"{lbl}={len(buckets[lbl])}" for lbl in buckets),
                file=sys.stderr,
            )

        # Estimate move count from header to avoid parsing the moves twice.
        # PlyCount header is reliably emitted by Lichess; fall back to
        # 0 (rejected) when missing rather than re-parsing.
        try:
            move_count = int(headers.get("PlyCount", "0"))
        except ValueError:
            move_count = 0

        label = _passes_filter(headers, move_count)
        if label is None:
            continue

        seen[label] += 1
        rng = rngs[label]
        bucket = buckets[label]
        if len(bucket) < per_bucket_sample:
            bucket.append(pgn_text)
            accepted += 1
        else:
            # Reservoir replacement: index in [0, seen[label]) with uniform prob.
            idx = rng.randint(0, seen[label] - 1)
            if idx < per_bucket_sample:
                bucket[idx] = pgn_text
                # `accepted` only counts first fills, not replacements

    elapsed = time.time() - start
    print(
        f"[stream] DONE — scanned {total_seen:,} games in {elapsed:,.0f}s "
        f"({total_seen / elapsed:,.0f}/s); per-bucket counts: "
        + " ".join(f"{lbl}={len(buckets[lbl])}" for lbl in buckets),
        file=sys.stderr,
    )
    return buckets


# ─── Checkpoint persistence ───────────────────────────────────────────────


def write_checkpoints(samples: dict[str, list[str]], checkpoint_dir: Path) -> None:
    """Write one PGN file per bucket to `checkpoint_dir/{label}.sample.pgn`.

    Filenames replace `≤` with `lte` and `+` with `plus` so paths are POSIX-safe.
    """
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    for label, pgns in samples.items():
        path = checkpoint_dir / f"{_safe_label(label)}.sample.pgn"
        path.write_text("\n\n".join(pgns) + "\n", encoding="utf-8")
        print(f"[checkpoint] wrote {path} ({len(pgns):,} games)", file=sys.stderr)


def read_checkpoints(checkpoint_dir: Path) -> dict[str, list[str]]:
    """Read previously-written per-bucket checkpoints back into memory."""
    import chess.pgn

    out: dict[str, list[str]] = {}
    for label, _, _ in BUCKET_DEFINITIONS:
        path = checkpoint_dir / f"{_safe_label(label)}.sample.pgn"
        if not path.exists():
            out[label] = []
            continue
        text = path.read_text(encoding="utf-8")
        # Split on the blank-line PGN separator. `chess.pgn.read_game` over a
        # StringIO would be slower; the explicit split is sufficient here.
        games = [seg.strip() for seg in text.split("\n\n\n") if seg.strip()]
        # Some writers emit only "\n\n" between games. Coalesce: if the split
        # yielded one giant blob, re-parse via chess.pgn.
        if len(games) <= 1 and text.count("[Event ") > 1:
            stream = io.StringIO(text)
            games = []
            while True:
                g = chess.pgn.read_game(stream)
                if g is None:
                    break
                games.append(str(g))
        out[label] = games
        print(f"[checkpoint] read {path} ({len(games):,} games)", file=sys.stderr)
    return out


def _safe_label(label: str) -> str:
    return label.replace("≤", "lte").replace("+", "plus")


# ─── Analysis (Phase 2 of the two-phase build) ────────────────────────────


def analyse_game(pgn_text: str, analyzer: Analyzer) -> GameStats:
    """Walk one game, compute per-game top1 + weighted-top1 + ACPL.

    Mirrors the audit-time formula in `heuristics.engine_correlation`:
      - top1_rate = (count where played == top_moves[0]) / eligible_plies
      - weighted_rate = Σ (complexity if played == top_moves[0]) / Σ complexity
      - acpl = mean(max(0, top1_eval - played_eval)) over eligible plies

    Eligible: not in book, not the only legal move (matches `_is_eligible`
    in engine_correlation/__init__.py:93).
    """
    import chess.pgn

    stream = io.StringIO(pgn_text)
    game = chess.pgn.read_game(stream)
    if game is None:
        return GameStats()

    board = game.board()
    top1 = 0
    weighted_top1 = 0.0
    total_weight = 0.0
    acpl_sum = 0.0
    eligible = 0
    ply = 0

    for move in game.mainline_moves():
        eval_result = analyzer.analyse(board, ply)
        ply += 1
        if not eval_result.is_book and not eval_result.is_only_move and eval_result.top_moves:
            played_uci = move.uci()
            top_uci = eval_result.top_moves[0].uci
            top_eval = eval_result.top_moves[0].eval_cp

            # Find played move in multipv, else penalise.
            played_eval: int | None = None
            for c in eval_result.top_moves:
                if c.uci == played_uci:
                    played_eval = c.eval_cp
                    break
            if played_eval is None:
                # Played move was below multipv depth — apply lower-bound penalty.
                worst_known_eval = eval_result.top_moves[-1].eval_cp
                played_eval = min(worst_known_eval, top_eval - ACPL_OUT_OF_MULTIPV_PENALTY_CP)

            cpl = max(0, top_eval - played_eval)
            acpl_sum += cpl
            eligible += 1
            if played_uci == top_uci:
                top1 += 1
            total_weight += eval_result.complexity_composite
            if played_uci == top_uci:
                weighted_top1 += eval_result.complexity_composite

        board.push(move)

    if eligible == 0:
        return GameStats()

    return GameStats(
        top1_rate=top1 / eligible,
        weighted_rate=(weighted_top1 / total_weight) if total_weight > 0 else 0.0,
        acpl=acpl_sum / eligible,
        eligible_plies=eligible,
    )


def analyse_samples(
    samples: dict[str, list[str]],
    analyzer_factory: Callable[[], Analyzer],
    *,
    progress_every: int = 50,
) -> dict[str, BucketStats]:
    """Run engine analysis over the sampled checkpoints, per bucket.

    Single-process, single-engine — multi-worker parallelism is left to a
    future revision; the current bottleneck is Stockfish CPU, not Python
    overhead. The `analyzer_factory` parameter exists so the caller can
    spawn one engine per worker if parallelising later.
    """
    out: dict[str, BucketStats] = {}
    analyzer = analyzer_factory()
    try:
        for label, _, _ in BUCKET_DEFINITIONS:
            low = next(rng[1] for rng in BUCKET_DEFINITIONS if rng[0] == label)
            high = next(rng[2] for rng in BUCKET_DEFINITIONS if rng[0] == label)
            stats = BucketStats(label=label, rating_low=low, rating_high=high)
            pgns = samples.get(label, [])
            start = time.time()
            for idx, pgn in enumerate(pgns):
                game_stats = analyse_game(pgn, analyzer)
                if game_stats.eligible_plies > 0:
                    stats.games.append(game_stats)
                if (idx + 1) % progress_every == 0:
                    elapsed = time.time() - start
                    rate = (idx + 1) / elapsed if elapsed > 0 else 0
                    print(
                        f"[analyse:{label}] {idx + 1:,}/{len(pgns):,} games ({rate:.1f}/s)",
                        file=sys.stderr,
                    )
            print(
                f"[analyse:{label}] DONE — {len(stats.games):,} games analysed",
                file=sys.stderr,
            )
            out[label] = stats
    finally:
        # Best-effort cleanup. Subprocess analyzers close on context exit;
        # static analyzers ignore close().
        close = getattr(analyzer, "close", None)
        if callable(close):
            close()
    return out


# ─── StockfishAnalyzer — real engine path ─────────────────────────────────


class StockfishAnalyzer:
    """Real Stockfish wrapper using python-chess SimpleEngine.

    Initialised lazily; one engine process per analyser instance. Forces
    Threads=1, Hash=256 for determinism (R6 — already the EngineAnalyzer
    default in analysis_core, replicated here so we don't take a runtime
    dependency on analysis-core from the heuristics package).
    """

    def __init__(self, command: str | list[str], *, depth: int, multipv: int = 3) -> None:
        self._command = command if isinstance(command, list) else command.split()
        self._depth = depth
        self._multipv = multipv
        self._engine: object | None = None  # chess.engine.SimpleEngine, lazy

    def _ensure_open(self) -> object:
        if self._engine is None:
            import chess.engine

            self._engine = chess.engine.SimpleEngine.popen_uci(self._command)
            self._engine.configure({"Threads": 1, "Hash": 256})
        return self._engine

    def analyse(self, board: object, ply: int) -> PositionEval:  # noqa: ARG002 — Protocol contract; ply unused here but required by Analyzer.analyse
        import chess
        import chess.engine

        engine = self._ensure_open()
        assert isinstance(engine, chess.engine.SimpleEngine)
        assert isinstance(board, chess.Board)

        legal = list(board.legal_moves)
        if not legal:
            return PositionEval(
                top_moves=(), complexity_composite=0.0, is_book=False, is_only_move=False
            )
        if len(legal) == 1:
            return PositionEval(
                top_moves=(), complexity_composite=0.0, is_book=False, is_only_move=True
            )

        multipv = min(self._multipv, len(legal))
        info_list = engine.analyse(board, chess.engine.Limit(depth=self._depth), multipv=multipv)
        if not isinstance(info_list, list):
            info_list = [info_list]

        top_moves: list[CandidateEval] = []
        for info in info_list:
            pv = info.get("pv") or []
            if not pv:
                continue
            move = pv[0]
            score = info.get("score")
            eval_cp = 0
            if score is not None:
                rel = score.relative
                mate = rel.mate()
                if mate is not None:
                    eval_cp = 30_000 if mate > 0 else -30_000
                else:
                    raw = rel.score()
                    if raw is not None:
                        eval_cp = int(raw)
            top_moves.append(CandidateEval(uci=move.uci(), eval_cp=eval_cp))

        # Complexity: simple proxy = log eval-span across the top_moves.
        # The audit-time engine_correlation signal multiplies by composite
        # complexity from the full analysis Position; for population stats
        # a coarser proxy is acceptable as long as we use the SAME formula
        # on both the audit side and here. The audit's complexity is
        # built by analysis_core._build_complexity; replicating it here
        # would create a maintenance trap. Instead we ship a deterministic
        # span-based composite that captures "how much daylight between
        # candidates" — the analysis side will be re-tuned in feature
        # 008 if the calibration drifts.
        if len(top_moves) >= 2:
            best_eval = top_moves[0].eval_cp
            worst_eval = top_moves[-1].eval_cp
            complexity = min(1.0, abs(best_eval - worst_eval) / 200.0)
        else:
            complexity = 0.0

        return PositionEval(
            top_moves=tuple(top_moves),
            complexity_composite=complexity,
            is_book=False,
            is_only_move=False,
        )

    def close(self) -> None:
        if self._engine is not None:
            import chess.engine

            assert isinstance(self._engine, chess.engine.SimpleEngine)
            self._engine.quit()
            self._engine = None


# ─── Bucket assembly ──────────────────────────────────────────────────────


def build_buckets_real(
    *,
    zst_path: Path,
    seed: int,
    per_bucket_sample: int,
    analyzer_factory: Callable[[], Analyzer],
    checkpoint_dir: Path,
    resume: bool,
) -> tuple[list[dict[str, object]], str]:
    """Real-data baseline build. Two-phase: stream + sample, then analyse.

    The Stockfish depth is captured by ``analyzer_factory`` at construction
    time (see ``StockfishAnalyzer.__init__``); not threaded through this
    signature to avoid an unused-parameter lint warning.

    Returns:
        (buckets, archive_sha256). The sha256 is computed once at start so
        the `source_dataset` label can quote it for reproducibility.
    """
    archive_sha = _sha256_of(zst_path)
    print(f"[setup] archive sha256: {archive_sha}", file=sys.stderr)

    # Phase 1: stream + sample (or restore from checkpoint).
    if resume and any(
        (checkpoint_dir / f"{_safe_label(lbl)}.sample.pgn").exists()
        for lbl, _, _ in BUCKET_DEFINITIONS
    ):
        print(f"[setup] resuming from checkpoint dir {checkpoint_dir}", file=sys.stderr)
        samples = read_checkpoints(checkpoint_dir)
    else:
        print(f"[setup] streaming + sampling from {zst_path}", file=sys.stderr)
        samples = reservoir_sample(
            _stream_pgn_games(zst_path),
            per_bucket_sample=per_bucket_sample,
            seed=seed,
        )
        write_checkpoints(samples, checkpoint_dir)

    # FR-001: enforce per-bucket floor.
    deficient: list[tuple[str, int]] = [
        (label, len(samples.get(label, [])))
        for label, _, _ in BUCKET_DEFINITIONS
        if len(samples.get(label, [])) < 1000
    ]
    if deficient:
        msg = "; ".join(f"{lbl} only has {n} samples (floor=1000)" for lbl, n in deficient)
        raise SystemExit(f"FR-001 violation — insufficient samples after streaming: {msg}")

    # Phase 2: engine analysis per bucket.
    stats_by_bucket = analyse_samples(samples, analyzer_factory)

    # Assemble 6 rated + 1 rating-unknown (elementwise median).
    rated: list[BucketStats] = [stats_by_bucket[label] for label, _, _ in BUCKET_DEFINITIONS]
    buckets: list[dict[str, object]] = [
        {
            "bucket_label": s.label,
            "rating_low": s.rating_low,
            "rating_high": s.rating_high,
            "expected_top1": round(s.expected_top1(), 4),
            "expected_weighted_top1": round(s.expected_weighted_top1(), 4),
            "expected_acpl_mean": round(s.expected_acpl_mean(), 2),
            "expected_acpl_stdev": round(s.expected_acpl_stdev(), 2),
            "sample_size": s.sample_size(),
        }
        for s in rated
    ]

    # 7th bucket: rating-unknown as elementwise median of the 6 rated buckets.
    buckets.append(
        {
            "bucket_label": "rating-unknown",
            "rating_low": None,
            "rating_high": None,
            "expected_top1": round(statistics.median(s.expected_top1() for s in rated), 4),
            "expected_weighted_top1": round(
                statistics.median(s.expected_weighted_top1() for s in rated), 4
            ),
            "expected_acpl_mean": round(
                statistics.median(s.expected_acpl_mean() for s in rated), 2
            ),
            "expected_acpl_stdev": round(
                statistics.median(s.expected_acpl_stdev() for s in rated), 2
            ),
            "sample_size": min(s.sample_size() for s in rated),
        }
    )

    return buckets, archive_sha


def _sha256_of(path: Path) -> str:
    """Stream the file through sha256 — works for the 28 GB archive."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ─── CLI ──────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate rating_baselines.json")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Emit hand-curated stub values (no archive + no engine). Phase 1 fallback.",
    )
    p.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Reservoir-sampling seed.")
    p.add_argument(
        "--month",
        default=DEFAULT_MONTH,
        help=f"Lichess month label (informational only — actual archive path comes "
        f"from --input-zst). Default: {DEFAULT_MONTH}.",
    )
    p.add_argument(
        "--input-zst",
        type=Path,
        default=DEFAULT_INPUT_ZST,
        help=f"Path to the Lichess .pgn.zst archive. Default: {DEFAULT_INPUT_ZST}",
    )
    p.add_argument(
        "--stockfish-cmd",
        default=DEFAULT_STOCKFISH_CMD,
        help=f"Shell command to launch the Stockfish UCI engine. "
        f"Default: {DEFAULT_STOCKFISH_CMD!r}",
    )
    p.add_argument(
        "--depth",
        type=int,
        default=DEFAULT_DEPTH,
        help=f"Stockfish depth. Default: {DEFAULT_DEPTH}.",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="(Reserved for future parallelism — currently single-engine.)",
    )
    p.add_argument(
        "--per-bucket-sample",
        type=int,
        default=DEFAULT_PER_BUCKET_SAMPLE,
        help=f"Reservoir sample size per bucket. Default: {DEFAULT_PER_BUCKET_SAMPLE}.",
    )
    p.add_argument(
        "--resume-from",
        type=Path,
        default=DEFAULT_CHECKPOINT_DIR,
        help=f"Checkpoint dir for Phase-2 restart. Default: {DEFAULT_CHECKPOINT_DIR}",
    )
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args(argv)

    if args.dry_run:
        buckets = build_buckets_stub()
        source = "hand-curated-stub (Phase 1 fallback; lit. values, not measured)"
    else:

        def _factory() -> Analyzer:
            return StockfishAnalyzer(args.stockfish_cmd, depth=args.depth)

        buckets, archive_sha = build_buckets_real(
            zst_path=args.input_zst,
            seed=args.seed,
            per_bucket_sample=args.per_bucket_sample,
            analyzer_factory=_factory,
            checkpoint_dir=args.resume_from,
            resume=True,
        )
        source = f"lichess_db_standard_rated_{args.month} (sha256={archive_sha})"

    payload = {
        "version": "2.0.0",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dataset": source,
        "buckets": buckets,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {args.output} ({len(buckets)} buckets, source={source})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
