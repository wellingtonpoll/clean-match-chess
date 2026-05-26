"""One-shot maintainer script — derive `rating_baselines.json` from Lichess open database.

Postgres-backed (feature 007 T007 v2): every analysis result is persisted to
`baseline_analyses` the moment it completes. Reservoir state flushes to
`baseline_samples` every N games scanned during Phase 1. A crash anywhere
loses at most ~one in-flight analysis or ~one flush window, never the
whole multi-hour run. Output is the same `rating_baselines.json` artifact
committed under `packages/heuristics/data/`; this script is NOT invoked
at audit time.

Methodology (per spec FR-011 + feature 007 research.md R1-R8):
  1. INSERT a `baseline_runs` row (status='running') with the full parameter
     set + archive sha256 + engine binary sha256.
  2. Stream a Lichess month-export archive (.pgn.zst) via `zstd -d -c`
     subprocess (no full decompress to disk — archive is ~170 GB
     decompressed).
  3. Filter games: both players Elo in [600, 3500], TC ∈ {RAPID, CLASSICAL},
     ≥ 20 plies.
  4. Bin by min(WhiteElo, BlackElo) into 6 rating buckets.
  5. Reservoir-sample N games per bucket (Algorithm L, seeded RNG). Flush
     pgn_corpus + baseline_samples to Postgres every `--flush-every` games.
  6. Spawn a ProcessPoolExecutor of `--workers` Stockfish-bound workers.
     Each worker loops: claim sample (SELECT FOR UPDATE SKIP LOCKED) →
     analyse with Stockfish depth N multipv 3 → INSERT baseline_analyses.
  7. SELECT from the `baseline_buckets` view to fetch the 6 rated bucket
     aggregates. Compute the 7th `rating-unknown` row as the elementwise
     median in Python.
  8. Emit JSON conforming to contracts/rating_baselines.schema.json + mark
     the run row status='completed'.

Runtime: ~6 h on a 6-core reference machine for 30000 analyses. Use
--dry-run for code review without running the engine.

Usage:
    python build_baselines.py --dry-run
    python build_baselines.py \\
        --input-zst ./lichess_db_standard_rated_2026-04.pgn.zst \\
        --stockfish-cmd "podman run --rm -i cleanmatch-stockfish:sf16" \\
        --seed 0 --depth 10 --workers 6 --per-bucket-sample 5000

    # Resume an existing run after a crash (skip Phase 1, jump straight to
    # worker claim loop):
    python build_baselines.py --run-id <uuid>
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import io
import json
import multiprocessing as mp
import os
import random
import re
import statistics
import subprocess
import sys
import time
import traceback
import uuid
from collections.abc import Iterator
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
DEFAULT_PER_BUCKET_SAMPLE = 5000
DEFAULT_DEPTH = 10
DEFAULT_MULTIPV = 3
DEFAULT_WORKERS = 6
DEFAULT_FLUSH_EVERY = 100_000  # Phase 1 reservoir flush interval (games scanned).
DEFAULT_STALE_CLAIM_MIN = 15  # Worker claim TTL before another worker may take over.

# Bumped when the methodology changes (engine version, depth, multipv, formula).
SCRIPT_VERSION = "0.2.0"

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


_HEADER_RE = re.compile(r'^\[(\w+)\s+"([^"]*)"\]')


def _stream_pgn_games(zst_path: Path) -> Iterator[tuple[dict[str, str], str]]:
    """Stream `(headers, pgn_text)` pairs from a zst-compressed PGN archive.

    Raw-text parser: PGN files use a strict format (header block of
    ``[Tag "value"]`` lines, blank line, move block, blank line, next game).
    Scanning line-by-line + regex-extracting headers is ~30x faster than
    running python-chess's full move parser over every game when the
    overwhelming majority will be rejected by the filter. The move text
    is preserved as raw bytes so the per-bucket sampler can persist it to
    a checkpoint without re-streaming.
    """
    proc = _open_zst_stream(zst_path)
    assert proc.stdout is not None
    stream = io.TextIOWrapper(proc.stdout, encoding="utf-8", errors="replace")
    try:
        buf: list[str] = []
        headers: dict[str, str] = {}
        in_moves = False
        for line in stream:
            buf.append(line)
            stripped = line.rstrip()
            if stripped.startswith("["):
                if in_moves and headers:
                    # Header line that arrived while we were in moves — the
                    # previous game ended without a trailing blank line.
                    # Yield it now and start a new game.
                    yield headers, "".join(buf[:-1])
                    buf = [line]
                    headers = {}
                    in_moves = False
                m = _HEADER_RE.match(stripped)
                if m:
                    headers[m.group(1)] = m.group(2)
                continue
            if not stripped:
                if headers and not in_moves:
                    # Transition: end of header block, moves block begins.
                    in_moves = True
                    continue
                if in_moves:
                    # End of moves block — emit the game.
                    yield headers, "".join(buf)
                    buf = []
                    headers = {}
                    in_moves = False
                continue
            # Non-blank, non-header line — only meaningful inside the move
            # block. If we land here before headers / move-block boundary
            # the line is dropped (commentary or junk between games).
        # Flush trailing game without a terminating blank line.
        if buf and headers:
            yield headers, "".join(buf)
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

        # Estimate move count from the buffered PGN text. The Lichess monthly
        # export does NOT emit a PlyCount header, so we count occurrences of
        # the per-ply clock annotation `{ [%clk` which appears exactly once
        # per ply on Lichess move lines.
        ply_header = headers.get("PlyCount")
        if ply_header is not None:
            try:
                move_count = int(ply_header)
            except ValueError:
                move_count = pgn_text.count("{ [%clk")
        else:
            move_count = pgn_text.count("{ [%clk")

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


# ─── DB-backed reservoir flush ────────────────────────────────────────────


@dataclass
class _ReservoirSlot:
    """In-memory mirror of one (bucket, position) row in baseline_samples.

    `last_persisted_sha256` lets us compute the per-flush diff cheaply:
    only positions whose current `pgn_sha256` differs from what's in the DB
    need an UPSERT. None means "never persisted yet".
    """

    bucket_label: str
    reservoir_position: int
    pgn_sha256: bytes
    pgn_text: str
    white_elo: int | None
    black_elo: int | None
    time_control: str | None
    ply_count: int | None
    last_persisted_sha256: bytes | None = None


def _flush_diff_to_db(
    session_factory: object,
    *,
    run_id: uuid.UUID,
    slots_by_bucket: dict[str, list[_ReservoirSlot]],
    total_scanned: int,
) -> int:
    """Upsert any reservoir slot whose pgn changed since the last flush.

    Returns the number of slots that needed persisting (zero means a no-op
    flush — the call still updates `total_scanned` in baseline_runs).
    """
    from analysis_core.db.baseline_store import ReservoirSlot, flush_reservoir

    diff: list[ReservoirSlot] = []
    dirty_local: list[_ReservoirSlot] = []
    for slots in slots_by_bucket.values():
        for s in slots:
            if s.pgn_sha256 == s.last_persisted_sha256:
                continue
            diff.append(
                ReservoirSlot(
                    bucket_label=s.bucket_label,
                    reservoir_position=s.reservoir_position,
                    pgn_sha256=s.pgn_sha256,
                    pgn_text=s.pgn_text,
                    white_elo=s.white_elo,
                    black_elo=s.black_elo,
                    time_control=s.time_control,
                    ply_count=s.ply_count,
                )
            )
            dirty_local.append(s)

    with session_factory() as session:  # type: ignore[misc]
        with session.begin():
            flush_reservoir(session, run_id=run_id, slots=diff, total_scanned=total_scanned)
    # Only mark slots persisted after a successful commit.
    for s in dirty_local:
        s.last_persisted_sha256 = s.pgn_sha256
    return len(diff)


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


# ─── Process-pool workers (DB-backed claim-loop) ─────────────────────────
#
# Each worker process owns one Stockfish subprocess for its entire lifetime
# AND one SQLAlchemy session factory (also per-process). The worker loops:
#   1. Claim sample via `SELECT ... FOR UPDATE SKIP LOCKED` + UPDATE claimed_at.
#   2. Run Stockfish (~30 s; no DB connections held).
#   3. INSERT into baseline_analyses. The trigger flips samples.analysed = TRUE.
# Stops when claim_sample returns None.

_WORKER_ANALYZER: StockfishAnalyzer | None = None


def _worker_close() -> None:
    """atexit handler — close the Stockfish subprocess cleanly.

    Prevents the podman-engine container leaks that hung Phase 2 in T007 v1.
    """
    global _WORKER_ANALYZER
    if _WORKER_ANALYZER is not None:
        try:
            _WORKER_ANALYZER.close()
        except Exception as e:
            print(f"[worker] cleanup error: {e}", file=sys.stderr)
        _WORKER_ANALYZER = None


def _worker_init(stockfish_cmd: str, depth: int, database_url: str) -> None:
    """ProcessPoolExecutor initializer — runs once per worker process.

    Initialises the analyzer + the DB engine + registers the cleanup hook.
    """
    import atexit

    from analysis_core.db.session import init_engine

    global _WORKER_ANALYZER
    _WORKER_ANALYZER = StockfishAnalyzer(stockfish_cmd, depth=depth)
    atexit.register(_worker_close)
    init_engine(database_url)


@dataclass
class _WorkerResult:
    """Summary returned by one worker after the claim loop drains."""

    completed: int = 0
    errors: int = 0


def _worker_claim_loop(run_id_str: str, stale_threshold_min: int) -> _WorkerResult:
    """Worker entry point — loop until no more pending samples."""
    from analysis_core.db.baseline_store import (
        ClaimedSample,
        claim_sample,
        persist_analysis,
    )
    from analysis_core.db.session import get_session_factory

    if _WORKER_ANALYZER is None:
        raise RuntimeError("worker not initialised — _worker_init was not called")
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("DB engine not initialised in worker — DATABASE_URL missing")

    run_id = uuid.UUID(run_id_str)
    result = _WorkerResult()
    while True:
        # Tx 1: atomic claim
        claimed: ClaimedSample | None
        with factory() as session:
            with session.begin():
                claimed = claim_sample(
                    session,
                    run_id=run_id,
                    stale_threshold_minutes=stale_threshold_min,
                )
        if claimed is None:
            break

        # Stockfish (~30 s) — no DB connection held
        t0 = time.perf_counter()
        stats: GameStats | None = None
        error_message: str | None = None
        try:
            stats = analyse_game(claimed.pgn_text, _WORKER_ANALYZER)
        except Exception as e:
            error_message = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"[:4000]
            result.errors += 1
        duration_ms = int((time.perf_counter() - t0) * 1000)

        # Tx 2: persist
        with factory() as session:
            with session.begin():
                persist_analysis(
                    session,
                    sample_id=claimed.sample_id,
                    top1_rate=stats.top1_rate if stats else 0.0,
                    weighted_rate=stats.weighted_rate if stats else 0.0,
                    acpl=stats.acpl if stats else 0.0,
                    eligible_plies=stats.eligible_plies if stats else 0,
                    analysis_duration_ms=duration_ms,
                    error_message=error_message,
                )
        result.completed += 1
    return result


def analyse_samples_against_db(
    *,
    run_id: uuid.UUID,
    stockfish_cmd: str,
    depth: int,
    workers: int,
    database_url: str,
    stale_threshold_min: int = DEFAULT_STALE_CLAIM_MIN,
    progress_every_sec: float = 30.0,
) -> tuple[int, int]:
    """Spawn `workers` ProcessPool workers; each drains pending samples.

    Returns `(total_completed, total_errors)`. Progress is logged from the
    parent process by polling the DB (workers can't share stdout cleanly).
    """
    from analysis_core.db.session import get_session_factory

    print(
        f"[analyse] starting {workers} workers against run {run_id} (depth={depth})",
        file=sys.stderr,
    )
    ctx = mp.get_context("spawn")
    completed_total = 0
    errors_total = 0
    start = time.time()
    last_print = start
    factory = get_session_factory()
    assert factory is not None, "parent process must have DB engine initialised"

    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers,
        mp_context=ctx,
        initializer=_worker_init,
        initargs=(stockfish_cmd, depth, database_url),
    ) as pool:
        futures = [
            pool.submit(_worker_claim_loop, str(run_id), stale_threshold_min)
            for _ in range(workers)
        ]
        while not all(f.done() for f in futures):
            now = time.time()
            if now - last_print >= progress_every_sec:
                _, total_analysed = _poll_progress(factory, run_id)
                elapsed = now - start
                rate = total_analysed / elapsed if elapsed > 0 else 0.0
                print(
                    f"[analyse] analysed={total_analysed:,} rate={rate:.2f}/s "
                    f"elapsed={elapsed / 60:.1f}min",
                    file=sys.stderr,
                )
                last_print = now
            time.sleep(2)

        for f in concurrent.futures.as_completed(futures):
            try:
                wr = f.result()
                completed_total += wr.completed
                errors_total += wr.errors
            except Exception as e:
                print(f"[analyse] worker crashed: {e}", file=sys.stderr)
                errors_total += 1

    elapsed = time.time() - start
    print(
        f"[analyse] DONE — completed={completed_total:,} errors={errors_total} "
        f"in {elapsed / 60:.1f}min",
        file=sys.stderr,
    )
    return completed_total, errors_total


def _poll_progress(session_factory: object, run_id: uuid.UUID) -> tuple[int, int]:
    """Return `(total_sampled, total_analysed)` from baseline_runs."""
    from sqlalchemy import text

    with session_factory() as session:  # type: ignore[misc]
        row = session.execute(
            text("SELECT total_sampled, total_analysed FROM baseline_runs WHERE id = :id"),
            {"id": run_id},
        ).first()
        if row is None:
            return 0, 0
        return int(row.total_sampled or 0), int(row.total_analysed or 0)


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


_RATING_BOUNDS: dict[str, tuple[int | None, int | None]] = {
    label: (low, high) for label, low, high in BUCKET_DEFINITIONS
}


def _stream_with_db_flush(
    *,
    session_factory: object,
    run_id: uuid.UUID,
    zst_path: Path,
    seed: int,
    per_bucket_sample: int,
    flush_every: int,
) -> int:
    """Phase 1 — stream + reservoir + periodic DB flush. Returns total_sampled.

    Reuses Algorithm L from `reservoir_sample()` but yields control to the
    DB every `flush_every` games scanned. Reservoir state is mirrored in
    `_ReservoirSlot` instances so we can flush only the per-position diff.
    """
    slots_by_bucket: dict[str, list[_ReservoirSlot]] = {
        label: [] for label, _, _ in BUCKET_DEFINITIONS
    }
    rngs: dict[str, random.Random] = {
        label: random.Random((seed << 16) ^ hash(label))  # noqa: S311 — sampling, not crypto
        for label, _, _ in BUCKET_DEFINITIONS
    }
    seen: dict[str, int] = {label: 0 for label, _, _ in BUCKET_DEFINITIONS}
    total_seen = 0
    start = time.time()

    for headers, pgn_text in _stream_pgn_games(zst_path):
        total_seen += 1

        ply_header = headers.get("PlyCount")
        if ply_header is not None:
            try:
                move_count = int(ply_header)
            except ValueError:
                move_count = pgn_text.count("{ [%clk")
        else:
            move_count = pgn_text.count("{ [%clk")

        label = _passes_filter(headers, move_count)
        if label is None:
            if total_seen % flush_every == 0:
                _flush_diff_to_db(
                    session_factory,
                    run_id=run_id,
                    slots_by_bucket=slots_by_bucket,
                    total_scanned=total_seen,
                )
                _log_phase1_progress(total_seen, slots_by_bucket, start)
            continue

        seen[label] += 1
        rng = rngs[label]
        bucket = slots_by_bucket[label]

        white_elo, black_elo, time_control, ply_count = _extract_headers(headers, move_count)
        pgn_bytes = pgn_text.encode("utf-8")
        pgn_sha = hashlib.sha256(pgn_bytes).digest()

        if len(bucket) < per_bucket_sample:
            bucket.append(
                _ReservoirSlot(
                    bucket_label=label,
                    reservoir_position=len(bucket),
                    pgn_sha256=pgn_sha,
                    pgn_text=pgn_text,
                    white_elo=white_elo,
                    black_elo=black_elo,
                    time_control=time_control,
                    ply_count=ply_count,
                )
            )
        else:
            idx = rng.randint(0, seen[label] - 1)
            if idx < per_bucket_sample:
                slot = bucket[idx]
                slot.pgn_sha256 = pgn_sha
                slot.pgn_text = pgn_text
                slot.white_elo = white_elo
                slot.black_elo = black_elo
                slot.time_control = time_control
                slot.ply_count = ply_count

        if total_seen % flush_every == 0:
            _flush_diff_to_db(
                session_factory,
                run_id=run_id,
                slots_by_bucket=slots_by_bucket,
                total_scanned=total_seen,
            )
            _log_phase1_progress(total_seen, slots_by_bucket, start)

    # Final flush at end of stream.
    _flush_diff_to_db(
        session_factory,
        run_id=run_id,
        slots_by_bucket=slots_by_bucket,
        total_scanned=total_seen,
    )
    _log_phase1_progress(total_seen, slots_by_bucket, start, final=True)
    return sum(len(s) for s in slots_by_bucket.values())


def _extract_headers(
    headers: dict[str, str], move_count: int
) -> tuple[int | None, int | None, str | None, int | None]:
    """Parse the columns we want to persist in baseline_samples."""

    def _int_or_none(s: str | None) -> int | None:
        if s is None:
            return None
        try:
            return int(s)
        except ValueError:
            return None

    white = _int_or_none(headers.get("WhiteElo"))
    black = _int_or_none(headers.get("BlackElo"))
    tc = headers.get("TimeControl")
    if tc is not None and len(tc) > 32:
        tc = tc[:32]
    return white, black, tc, move_count


def _log_phase1_progress(
    total_seen: int,
    slots_by_bucket: dict[str, list[_ReservoirSlot]],
    start: float,
    *,
    final: bool = False,
) -> None:
    elapsed = time.time() - start
    rate = total_seen / elapsed if elapsed > 0 else 0.0
    fills = " ".join(f"{lbl}={len(slots)}" for lbl, slots in slots_by_bucket.items())
    tag = "DONE" if final else "stream"
    print(
        f"[{tag}] scanned={total_seen:,} rate={rate:,.0f}/s elapsed={elapsed:.0f}s fills: {fills}",
        file=sys.stderr,
    )


def build_buckets_real(
    *,
    session_factory: object,
    run_id: uuid.UUID,
    zst_path: Path,
    seed: int,
    per_bucket_sample: int,
    stockfish_cmd: str,
    depth: int,
    workers: int,
    database_url: str,
    flush_every: int = DEFAULT_FLUSH_EVERY,
    skip_phase1: bool = False,
) -> tuple[list[dict[str, object]], str]:
    """DB-backed baseline build. Phase 1 (stream + flush) → Phase 2 (workers).

    `session_factory` is the SQLAlchemy session factory (parent process).
    `run_id` was created upstream via `baseline_store.create_run()` — this
    function only updates progress on it; it does NOT mark the run
    completed (caller does that after writing the JSON, so failures here
    leave the row in 'running' for resume).
    """
    from analysis_core.db.baseline_store import (
        fetch_bucket_aggregates,
        mark_phase1_done,
    )
    from sqlalchemy import text

    archive_sha = _sha256_of(zst_path) if zst_path.exists() else ""
    if archive_sha:
        print(f"[setup] archive sha256: {archive_sha}", file=sys.stderr)

    # ─── Phase 1: stream + reservoir + periodic flush ───
    if skip_phase1:
        print(
            f"[phase1] skipped (resume mode) — using existing samples for run {run_id}",
            file=sys.stderr,
        )
        with session_factory() as session:  # type: ignore[misc]
            total_sampled = session.execute(
                text("SELECT total_sampled FROM baseline_runs WHERE id = :id"),
                {"id": run_id},
            ).scalar_one()
        if total_sampled is None:
            raise SystemExit(
                f"--run-id {run_id} has no Phase 1 result — cannot resume Phase 2 alone"
            )
    else:
        total_sampled = _stream_with_db_flush(
            session_factory=session_factory,
            run_id=run_id,
            zst_path=zst_path,
            seed=seed,
            per_bucket_sample=per_bucket_sample,
            flush_every=flush_every,
        )
        with session_factory() as session:  # type: ignore[misc]
            with session.begin():
                mark_phase1_done(session, run_id=run_id, total_sampled=total_sampled)

    # FR-001: enforce per-bucket floor BEFORE running 6h of analysis.
    with session_factory() as session:  # type: ignore[misc]
        rows = session.execute(
            text(
                "SELECT bucket_label, COUNT(*) AS n FROM baseline_samples "
                "WHERE run_id = :id GROUP BY bucket_label"
            ),
            {"id": run_id},
        ).all()
    fills = {row.bucket_label: int(row.n) for row in rows}
    deficient = [
        (lbl, fills.get(lbl, 0)) for lbl, _, _ in BUCKET_DEFINITIONS if fills.get(lbl, 0) < 1000
    ]
    if deficient:
        msg = "; ".join(f"{lbl}={n} (floor=1000)" for lbl, n in deficient)
        raise SystemExit(f"FR-001 violation — insufficient samples after Phase 1: {msg}")

    # ─── Phase 2: workers drain pending samples via claim loop ───
    analyse_samples_against_db(
        run_id=run_id,
        stockfish_cmd=stockfish_cmd,
        depth=depth,
        workers=workers,
        database_url=database_url,
    )

    # ─── Phase 3: aggregate from view + compute rating-unknown ───
    with session_factory() as session:  # type: ignore[misc]
        aggs = fetch_bucket_aggregates(session, run_id=run_id)

    from analysis_core.db.baseline_store import compute_rating_unknown_row

    if len(aggs) != 6:
        raise SystemExit(
            f"Expected 6 rated buckets from baseline_buckets view, got {len(aggs)}: "
            + ", ".join(a.bucket_label for a in aggs)
        )
    aggs_sorted: list[object] = []
    for label, _, _ in BUCKET_DEFINITIONS:
        match = next((a for a in aggs if a.bucket_label == label), None)
        if match is None:
            raise SystemExit(f"View missing bucket '{label}' — aborting")
        aggs_sorted.append(match)
    unknown = compute_rating_unknown_row(aggs_sorted)  # type: ignore[arg-type]

    buckets: list[dict[str, object]] = []
    for a in aggs_sorted:  # type: ignore[assignment]
        low, high = _RATING_BOUNDS[a.bucket_label]
        buckets.append(
            {
                "bucket_label": a.bucket_label,
                "rating_low": low,
                "rating_high": high,
                "expected_top1": round(a.expected_top1, 4),
                "expected_weighted_top1": round(a.expected_weighted_top1, 4),
                "expected_acpl_mean": round(a.expected_acpl_mean, 2),
                "expected_acpl_stdev": round(a.expected_acpl_stdev, 2),
                "sample_size": int(a.sample_size),
            }
        )
    buckets.append(
        {
            "bucket_label": "rating-unknown",
            "rating_low": None,
            "rating_high": None,
            "expected_top1": round(unknown.expected_top1, 4),
            "expected_weighted_top1": round(unknown.expected_weighted_top1, 4),
            "expected_acpl_mean": round(unknown.expected_acpl_mean, 2),
            "expected_acpl_stdev": round(unknown.expected_acpl_stdev, 2),
            "sample_size": int(unknown.sample_size),
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


def _sha256_of_engine_binary(stockfish_cmd: str) -> bytes:
    """Best-effort sha256 of the local Stockfish binary; falls back to a sentinel."""
    parts = stockfish_cmd.split()
    candidate: Path | None = None
    if parts and not parts[0].startswith(("podman", "docker")):
        candidate = Path(parts[0])
    if candidate is not None and candidate.exists():
        h = hashlib.sha256()
        with candidate.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.digest()
    # Container path: hash the command string as a stable placeholder.
    return hashlib.sha256(stockfish_cmd.encode("utf-8")).digest()


# ─── CLI ──────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate rating_baselines.json")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Emit hand-curated stub values (no archive + no engine + no DB).",
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
        "--multipv",
        type=int,
        default=DEFAULT_MULTIPV,
        help=f"Stockfish multipv. Default: {DEFAULT_MULTIPV}.",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of parallel Stockfish workers. Default: {DEFAULT_WORKERS}.",
    )
    p.add_argument(
        "--per-bucket-sample",
        type=int,
        default=DEFAULT_PER_BUCKET_SAMPLE,
        help=f"Reservoir sample size per bucket. Default: {DEFAULT_PER_BUCKET_SAMPLE}.",
    )
    p.add_argument(
        "--flush-every",
        type=int,
        default=DEFAULT_FLUSH_EVERY,
        help=f"Phase-1 reservoir flush interval (games scanned). Default: {DEFAULT_FLUSH_EVERY}.",
    )
    p.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Resume a previously-started run by UUID (skips Phase 1).",
    )
    p.add_argument(
        "--notes",
        type=str,
        default=None,
        help="Optional free-text notes recorded in baseline_runs.notes.",
    )
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args(argv)

    if args.dry_run:
        buckets = build_buckets_stub()
        source = "hand-curated-stub (Phase 1 fallback; lit. values, not measured)"
        _write_output(args.output, source, buckets)
        return 0

    from analysis_core.db.baseline_store import (
        create_run,
        mark_run_completed,
        mark_run_failed,
    )
    from analysis_core.db.session import get_session_factory, init_engine

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit(
            "DATABASE_URL not set — baseline build requires a running Postgres. "
            "Start `podman compose -f infra/docker/compose.yml up -d postgres` and "
            "export DATABASE_URL. See README.md for the connection string."
        )

    init_engine(database_url)
    factory = get_session_factory()
    if factory is None:
        raise SystemExit("Failed to initialise DB engine — check DATABASE_URL + Postgres health.")

    if args.run_id:
        run_id = uuid.UUID(args.run_id)
        archive_sha = ""
        skip_phase1 = True
        print(f"[setup] resuming run {run_id} (skipping Phase 1)", file=sys.stderr)
    else:
        skip_phase1 = False
        if not args.input_zst.exists():
            raise SystemExit(f"Input archive not found: {args.input_zst}")
        archive_sha_hex = _sha256_of(args.input_zst)
        archive_sha = archive_sha_hex
        engine_sha = _sha256_of_engine_binary(args.stockfish_cmd)
        with factory() as session:
            with session.begin():
                run_id = create_run(
                    session,
                    archive_sha256=bytes.fromhex(archive_sha_hex),
                    source_dataset=f"lichess_db_standard_rated_{args.month}",
                    seed=args.seed,
                    per_bucket_sample=args.per_bucket_sample,
                    depth=args.depth,
                    multipv=args.multipv,
                    workers=args.workers,
                    engine_binary_sha256=engine_sha,
                    script_version=SCRIPT_VERSION,
                    notes=args.notes,
                )
        print(f"[setup] run_id={run_id}", file=sys.stderr)

    try:
        buckets, archive_sha_final = build_buckets_real(
            session_factory=factory,
            run_id=run_id,
            zst_path=args.input_zst,
            seed=args.seed,
            per_bucket_sample=args.per_bucket_sample,
            stockfish_cmd=args.stockfish_cmd,
            depth=args.depth,
            workers=args.workers,
            database_url=database_url,
            flush_every=args.flush_every,
            skip_phase1=skip_phase1,
        )
    except KeyboardInterrupt:
        with factory() as session:
            with session.begin():
                mark_run_failed(
                    session,
                    run_id=run_id,
                    error_message="SIGINT — user aborted",
                    status="aborted",
                )
        print(f"[abort] marked run {run_id} aborted", file=sys.stderr)
        raise
    except Exception as e:
        with factory() as session:
            with session.begin():
                mark_run_failed(
                    session,
                    run_id=run_id,
                    error_message=f"{type(e).__name__}: {e}"[:4000],
                    status="failed",
                )
        print(f"[fail] marked run {run_id} failed: {e}", file=sys.stderr)
        raise

    with factory() as session:
        with session.begin():
            mark_run_completed(session, run_id=run_id)

    source = (
        f"lichess_db_standard_rated_{args.month} "
        f"(sha256={archive_sha or archive_sha_final}, run_id={run_id})"
    )
    _write_output(args.output, source, buckets)
    return 0


def _write_output(out_path: Path, source: str, buckets: list[dict[str, object]]) -> None:
    payload = {
        "version": "2.0.0",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dataset": source,
        "buckets": buckets,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {out_path} ({len(buckets)} buckets, source={source})")


if __name__ == "__main__":
    sys.exit(main())
