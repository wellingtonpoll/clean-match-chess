"""RatingBaselines contract tests (T013)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from heuristics.rating_baselines import (
    RatingBaselines,
    get_baselines,
    reset_cache,
)


def test_bucket_for_lower_bound() -> None:
    bl = get_baselines()
    bucket = bl.bucket_for(1201)
    assert bucket.bucket_label == "1201-1500"


def test_bucket_for_upper_bound_inclusive() -> None:
    bl = get_baselines()
    # 1500 is the inclusive upper bound of "1201-1500".
    bucket = bl.bucket_for(1500)
    assert bucket.bucket_label == "1201-1500"


def test_bucket_for_just_above_boundary() -> None:
    bl = get_baselines()
    bucket = bl.bucket_for(1501)
    assert bucket.bucket_label == "1501-1800"


def test_bucket_for_none_returns_rating_unknown() -> None:
    bl = get_baselines()
    bucket = bl.bucket_for(None)
    assert bucket.bucket_label == "rating-unknown"


def test_bucket_for_far_out_of_range_returns_rating_unknown() -> None:
    bl = get_baselines()
    assert bl.bucket_for(99999).bucket_label == "rating-unknown"


def test_bucket_for_negative_returns_rating_unknown() -> None:
    bl = get_baselines()
    assert bl.bucket_for(-5).bucket_label == "rating-unknown"


def test_bucket_for_zero_returns_rating_unknown() -> None:
    bl = get_baselines()
    assert bl.bucket_for(0).bucket_label == "rating-unknown"


def test_for_label_returns_matching_bucket() -> None:
    bl = get_baselines()
    bucket = bl.for_label("2401+")
    assert bucket.bucket_label == "2401+"
    assert bucket.rating_low == 2401


def test_baselines_have_all_seven_buckets() -> None:
    bl = get_baselines()
    labels = {b.bucket_label for b in bl.buckets}
    assert labels == {
        "≤1200",
        "1201-1500",
        "1501-1800",
        "1801-2100",
        "2101-2400",
        "2401+",
        "rating-unknown",
    }


def test_schema_validation_rejects_bad_payload(tmp_path: Path) -> None:
    # Write an obviously malformed baselines file and ensure load raises.
    bad = tmp_path / "rating_baselines.json"
    bad.write_text(json.dumps({"version": "1.0.0"}))  # missing buckets
    reset_cache()
    with pytest.raises(ValueError):
        get_baselines(bad)
    reset_cache()  # restore module-level cache to None for other tests


def test_schema_validation_rejects_wrong_bucket_count(tmp_path: Path) -> None:
    bad = tmp_path / "rating_baselines.json"
    bad.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "generated_at": "2026-05-24T00:00:00Z",
                "source_dataset": "stub",
                "buckets": [],
            }
        )
    )
    reset_cache()
    with pytest.raises(ValueError):
        get_baselines(bad)
    reset_cache()


def test_returns_rating_baselines_instance() -> None:
    assert isinstance(get_baselines(), RatingBaselines)
