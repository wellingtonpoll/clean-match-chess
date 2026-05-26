"""Repository layer for the baseline-build pipeline (feature 007).

Backs `packages/heuristics/scripts/build_baselines.py`. All DB writes
flow through this module so the script stays orchestration-only and the
SQL stays auditable. Unlike `cache.py`, these functions DO raise on DB
errors — a baseline build is a maintainer operation, not a user-facing
audit; failures should crash visibly rather than silently degrade.

The module is sync and uses short transactions per operation. Worker
subprocesses initialise their own engine via `init_engine()` (idempotent
process-global).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from sqlalchemy import insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from analysis_core.db.models import (
    BaselineAnalysisModel,
    BaselineRunModel,
    BaselineSampleModel,
    PgnCorpusModel,
)


@dataclass(frozen=True)
class ClaimedSample:
    """Result of `claim_sample()` — pending sample ready for analysis."""

    sample_id: uuid.UUID
    pgn_text: str
    bucket_label: str


@dataclass(frozen=True)
class BucketAggregate:
    """One row from the `baseline_buckets` view."""

    bucket_label: str
    sample_size: int
    expected_top1: float
    expected_weighted_top1: float
    expected_acpl_mean: float
    expected_acpl_stdev: float


@dataclass(frozen=True)
class ReservoirSlot:
    """One reservoir position to be persisted in a flush."""

    bucket_label: str
    reservoir_position: int
    pgn_sha256: bytes
    pgn_text: str
    white_elo: int | None
    black_elo: int | None
    time_control: str | None
    ply_count: int | None


_STALE_CLAIM_MINUTES = 15

# psycopg caps each query at 65535 placeholders. baseline_samples has 8
# inserted params per row, so 8000 rows x 8 params = 64000 (under the limit
# with some headroom). pgn_corpus is 2 params per row, but we chunk it
# the same way for simplicity.
_INSERT_CHUNK_SIZE = 5000


def create_run(
    session: Session,
    *,
    archive_sha256: bytes,
    source_dataset: str,
    seed: int,
    per_bucket_sample: int,
    depth: int,
    multipv: int,
    workers: int,
    engine_binary_sha256: bytes,
    script_version: str,
    notes: str | None = None,
) -> uuid.UUID:
    """Insert a new `baseline_runs` row with status='running'. Returns the run id."""
    run = BaselineRunModel(
        archive_sha256=archive_sha256,
        source_dataset=source_dataset,
        seed=seed,
        per_bucket_sample=per_bucket_sample,
        depth=depth,
        multipv=multipv,
        workers=workers,
        engine_binary_sha256=engine_binary_sha256,
        script_version=script_version,
        notes=notes,
    )
    session.add(run)
    session.flush()  # populates run.id from server_default
    return run.id


def flush_reservoir(
    session: Session,
    *,
    run_id: uuid.UUID,
    slots: list[ReservoirSlot],
    total_scanned: int | None = None,
) -> None:
    """Upsert pgn_corpus + baseline_samples for the given diff.

    Uses `ON CONFLICT DO NOTHING` for pgn_corpus (idempotent) and
    `ON CONFLICT (run_id, bucket_label, reservoir_position) DO UPDATE`
    for baseline_samples (Algorithm-L overwrites slots in place).

    Optionally updates `baseline_runs.total_scanned` in the same tx.
    """
    if not slots:
        if total_scanned is not None:
            session.execute(
                update(BaselineRunModel)
                .where(BaselineRunModel.id == run_id)
                .values(total_scanned=total_scanned)
            )
        return

    # Chunk both upserts to stay under psycopg's 65535-param-per-query cap.
    for chunk_start in range(0, len(slots), _INSERT_CHUNK_SIZE):
        chunk = slots[chunk_start : chunk_start + _INSERT_CHUNK_SIZE]
        session.execute(
            pg_insert(PgnCorpusModel)
            .values([{"pgn_sha256": s.pgn_sha256, "pgn_text": s.pgn_text} for s in chunk])
            .on_conflict_do_nothing(index_elements=["pgn_sha256"])
        )
        sample_rows = [
            {
                "run_id": run_id,
                "bucket_label": s.bucket_label,
                "pgn_sha256": s.pgn_sha256,
                "white_elo": s.white_elo,
                "black_elo": s.black_elo,
                "time_control": s.time_control,
                "ply_count": s.ply_count,
                "reservoir_position": s.reservoir_position,
            }
            for s in chunk
        ]
        stmt = pg_insert(BaselineSampleModel).values(sample_rows)
        stmt = stmt.on_conflict_do_update(
            constraint="baseline_samples_position_unique",
            set_={
                "pgn_sha256": stmt.excluded.pgn_sha256,
                "white_elo": stmt.excluded.white_elo,
                "black_elo": stmt.excluded.black_elo,
                "time_control": stmt.excluded.time_control,
                "ply_count": stmt.excluded.ply_count,
                "sampled_at": text("NOW()"),
                "claimed_at": None,
                "analysed": False,
            },
        )
        session.execute(stmt)

    if total_scanned is not None:
        session.execute(
            update(BaselineRunModel)
            .where(BaselineRunModel.id == run_id)
            .values(total_scanned=total_scanned)
        )


def mark_phase1_done(session: Session, *, run_id: uuid.UUID, total_sampled: int) -> None:
    """Record `total_sampled` once Phase 1 (stream + reservoir) completes."""
    session.execute(
        update(BaselineRunModel)
        .where(BaselineRunModel.id == run_id)
        .values(total_sampled=total_sampled)
    )


def claim_sample(
    session: Session,
    *,
    run_id: uuid.UUID,
    stale_threshold_minutes: int = _STALE_CLAIM_MINUTES,
) -> ClaimedSample | None:
    """Atomically claim the next pending sample for analysis.

    Uses `FOR UPDATE SKIP LOCKED` on `baseline_samples`, then UPDATEs
    `claimed_at = NOW()`. The caller must commit the surrounding
    transaction before doing the Stockfish analysis — that releases the
    row-level lock so other workers can move on while this one is busy.

    A sample is re-claimable when `claimed_at < NOW() - stale_threshold`
    AND `analysed = FALSE` (covers workers that crashed mid-analysis).
    """
    stmt = text(
        """
        SELECT s.id, s.bucket_label, c.pgn_text
        FROM baseline_samples s
        JOIN pgn_corpus c ON c.pgn_sha256 = s.pgn_sha256
        WHERE s.run_id = :run_id
          AND s.analysed = FALSE
          AND (
            s.claimed_at IS NULL
            OR s.claimed_at < NOW() - make_interval(mins => :stale)
          )
        ORDER BY s.claimed_at NULLS FIRST, s.id
        FOR UPDATE OF s SKIP LOCKED
        LIMIT 1
        """
    )
    row = session.execute(stmt, {"run_id": run_id, "stale": stale_threshold_minutes}).first()
    if row is None:
        return None
    session.execute(
        text("UPDATE baseline_samples SET claimed_at = NOW() WHERE id = :id"),
        {"id": row.id},
    )
    return ClaimedSample(sample_id=row.id, pgn_text=row.pgn_text, bucket_label=row.bucket_label)


def persist_analysis(
    session: Session,
    *,
    sample_id: uuid.UUID,
    top1_rate: float,
    weighted_rate: float,
    acpl: float,
    eligible_plies: int,
    analysis_duration_ms: int | None = None,
    error_message: str | None = None,
) -> None:
    """Insert a row into `baseline_analyses` (trigger flips sample.analysed)."""
    session.execute(
        insert(BaselineAnalysisModel).values(
            sample_id=sample_id,
            top1_rate=top1_rate,
            weighted_rate=weighted_rate,
            acpl=acpl,
            eligible_plies=eligible_plies,
            analysis_duration_ms=analysis_duration_ms,
            error_message=error_message,
        )
    )
    session.execute(
        update(BaselineRunModel)
        .where(
            BaselineRunModel.id
            == select(BaselineSampleModel.run_id)
            .where(BaselineSampleModel.id == sample_id)
            .scalar_subquery()
        )
        .values(total_analysed=BaselineRunModel.total_analysed + 1)
    )


def mark_run_completed(session: Session, *, run_id: uuid.UUID) -> None:
    session.execute(
        update(BaselineRunModel)
        .where(BaselineRunModel.id == run_id)
        .values(status="completed", finished_at=text("NOW()"))
    )


def mark_run_failed(
    session: Session,
    *,
    run_id: uuid.UUID,
    error_message: str,
    status: str = "failed",
) -> None:
    if status not in ("failed", "aborted"):
        raise ValueError(f"invalid terminal status: {status}")
    session.execute(
        update(BaselineRunModel)
        .where(BaselineRunModel.id == run_id)
        .values(status=status, finished_at=text("NOW()"), error_message=error_message)
    )


def fetch_bucket_aggregates(session: Session, *, run_id: uuid.UUID) -> list[BucketAggregate]:
    """SELECT from the `baseline_buckets` view for one run.

    Returns 6 rows max (one per rated bucket); the 7th rating-unknown row
    is computed by `compute_rating_unknown_row()` from these.
    """
    stmt = text(
        """
        SELECT bucket_label, sample_size, expected_top1, expected_weighted_top1,
               expected_acpl_mean, expected_acpl_stdev
        FROM baseline_buckets
        WHERE run_id = :run_id
        ORDER BY bucket_label
        """
    )
    return [
        BucketAggregate(
            bucket_label=row.bucket_label,
            sample_size=row.sample_size,
            expected_top1=row.expected_top1,
            expected_weighted_top1=row.expected_weighted_top1,
            expected_acpl_mean=row.expected_acpl_mean,
            expected_acpl_stdev=row.expected_acpl_stdev,
        )
        for row in session.execute(stmt, {"run_id": run_id})
    ]


def compute_rating_unknown_row(buckets: list[BucketAggregate]) -> BucketAggregate:
    """Elementwise median of the 6 rated buckets for the rating-unknown row.

    Matches the previous in-memory build_buckets_real() behaviour: each
    field is the median across the rated buckets. sample_size is the min
    (most-conservative bound).
    """
    if not buckets:
        raise ValueError("cannot compute rating-unknown row from empty bucket list")

    def _median(values: list[float]) -> float:
        sorted_v = sorted(values)
        n = len(sorted_v)
        mid = n // 2
        if n % 2 == 1:
            return sorted_v[mid]
        return (sorted_v[mid - 1] + sorted_v[mid]) / 2

    return BucketAggregate(
        bucket_label="rating-unknown",
        sample_size=min(b.sample_size for b in buckets),
        expected_top1=_median([b.expected_top1 for b in buckets]),
        expected_weighted_top1=_median([b.expected_weighted_top1 for b in buckets]),
        expected_acpl_mean=_median([b.expected_acpl_mean for b in buckets]),
        expected_acpl_stdev=_median([b.expected_acpl_stdev for b in buckets]),
    )


def measure_ms(start_perf_counter: float) -> int:
    """Convert a `time.perf_counter()` start mark into elapsed ms."""
    return int((time.perf_counter() - start_perf_counter) * 1000)
