"""Rating-baseline lookup (T006, FR-010, FR-008).

Bundled lookup of expected play statistics per rating bucket. Lazy-loaded
on first call (NOT at module import) so test discovery does not require
the JSON to exist; failures surface at use site with a clear message.

Public API:

    from heuristics.rating_baselines import get_baselines
    baselines = get_baselines()
    bucket = baselines.bucket_for(1500)        # → RatingBaseline
    same   = baselines.for_label("1501-1800")  # → RatingBaseline

The JSON is validated against the schema at
`specs/004-scoring-v2-phase1/contracts/rating_baselines.schema.json`. The
validator below implements the subset of JSON Schema actually used by the
contract (required keys, enum, numeric range, exact-cardinality bucket
array) — sufficient to catch artifact corruption without pulling
`jsonschema` as a dep.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

BASELINES_PATH: Final[Path] = Path(__file__).resolve().parents[3] / "data" / "rating_baselines.json"

_ALLOWED_BUCKET_LABELS: Final[tuple[str, ...]] = (
    "≤1200",
    "1201-1500",
    "1501-1800",
    "1801-2100",
    "2101-2400",
    "2401+",
    "rating-unknown",
)

_REQUIRED_BUCKET_KEYS: Final[tuple[str, ...]] = (
    "bucket_label",
    "rating_low",
    "rating_high",
    "expected_top1",
    "expected_weighted_top1",
    "expected_acpl_mean",
    "expected_acpl_stdev",
    "sample_size",
)

_REQUIRED_TOP_KEYS: Final[tuple[str, ...]] = (
    "version",
    "generated_at",
    "source_dataset",
    "buckets",
)


@dataclass(frozen=True, slots=True)
class RatingBaseline:
    """One entry in the bundled rating-baselines lookup."""

    bucket_label: str
    rating_low: int | None
    rating_high: int | None
    expected_top1: float
    expected_weighted_top1: float
    expected_acpl_mean: float
    expected_acpl_stdev: float
    sample_size: int


@dataclass(frozen=True, slots=True)
class RatingBaselines:
    """Container for all per-bucket baselines plus dataset provenance."""

    version: str
    generated_at: str
    source_dataset: str
    buckets: tuple[RatingBaseline, ...]

    def bucket_for(self, rating: int | None) -> RatingBaseline:
        """Return the baseline matching `rating`; rating-unknown for None/out-of-range."""
        if rating is None or rating <= 0 or rating > 3500:
            return self.for_label("rating-unknown")
        for b in self.buckets:
            if (
                b.rating_low is not None
                and b.rating_high is not None
                and b.rating_low <= rating <= b.rating_high
            ):
                return b
        return self.for_label("rating-unknown")

    def for_label(self, bucket_label: str) -> RatingBaseline:
        for b in self.buckets:
            if b.bucket_label == bucket_label:
                return b
        raise KeyError(f"unknown rating bucket label: {bucket_label!r}")


_BASELINES: RatingBaselines | None = None


def get_baselines(path: Path | None = None) -> RatingBaselines:
    """Return the lazily-loaded baselines. Validated on first call."""
    global _BASELINES
    if _BASELINES is None or path is not None:
        target = path or BASELINES_PATH
        loaded = _load_and_validate(target)
        if path is None:
            _BASELINES = loaded
        return loaded
    return _BASELINES


def reset_cache() -> None:
    """Clear the module-level cache (test-only helper)."""
    global _BASELINES
    _BASELINES = None


def _load_and_validate(path: Path) -> RatingBaselines:
    if not path.is_file():
        raise FileNotFoundError(
            f"rating baselines not found at {path}; "
            "run packages/heuristics/scripts/build_baselines.py --dry-run to materialise"
        )
    raw = json.loads(path.read_text())
    _validate_top_level(raw)
    buckets = tuple(_build_bucket(entry) for entry in raw["buckets"])
    _validate_buckets(buckets)
    return RatingBaselines(
        version=raw["version"],
        generated_at=raw["generated_at"],
        source_dataset=raw["source_dataset"],
        buckets=buckets,
    )


def _validate_top_level(raw: object) -> None:
    if not isinstance(raw, dict):
        raise ValueError("rating_baselines.json root must be an object")
    missing = [k for k in _REQUIRED_TOP_KEYS if k not in raw]
    if missing:
        raise ValueError(f"rating_baselines.json missing required keys: {missing}")
    if not isinstance(raw["version"], str):
        raise ValueError("rating_baselines.json `version` must be a string")
    if not isinstance(raw["buckets"], list):
        raise ValueError("rating_baselines.json `buckets` must be an array")
    if len(raw["buckets"]) != 7:
        raise ValueError(
            f"rating_baselines.json must have exactly 7 buckets, got {len(raw['buckets'])}"
        )


def _build_bucket(entry: object) -> RatingBaseline:
    if not isinstance(entry, dict):
        raise ValueError(f"bucket entry must be an object, got {type(entry).__name__}")
    missing = [k for k in _REQUIRED_BUCKET_KEYS if k not in entry]
    if missing:
        raise ValueError(f"bucket missing required keys: {missing}")
    label = entry["bucket_label"]
    if label not in _ALLOWED_BUCKET_LABELS:
        raise ValueError(f"unknown bucket_label: {label!r}")
    rating_low = entry["rating_low"]
    rating_high = entry["rating_high"]
    if rating_low is not None and not isinstance(rating_low, int):
        raise ValueError(f"rating_low must be int or null, got {type(rating_low).__name__}")
    if rating_high is not None and not isinstance(rating_high, int):
        raise ValueError(f"rating_high must be int or null, got {type(rating_high).__name__}")
    sample_size = entry["sample_size"]
    if not isinstance(sample_size, int) or sample_size < 100:
        raise ValueError(f"sample_size must be int >= 100, got {sample_size!r}")
    expected_top1 = _check_unit(entry["expected_top1"], "expected_top1")
    expected_weighted_top1 = _check_unit(entry["expected_weighted_top1"], "expected_weighted_top1")
    expected_acpl_mean = _check_acpl(entry["expected_acpl_mean"], "expected_acpl_mean")
    expected_acpl_stdev = _check_acpl(entry["expected_acpl_stdev"], "expected_acpl_stdev")
    return RatingBaseline(
        bucket_label=label,
        rating_low=rating_low,
        rating_high=rating_high,
        expected_top1=expected_top1,
        expected_weighted_top1=expected_weighted_top1,
        expected_acpl_mean=expected_acpl_mean,
        expected_acpl_stdev=expected_acpl_stdev,
        sample_size=sample_size,
    )


def _check_unit(value: object, name: str) -> float:
    v = _check_number(value, name)
    if not 0.0 <= v <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {v}")
    return v


def _check_acpl(value: object, name: str) -> float:
    v = _check_number(value, name)
    if not 0.0 <= v <= 500.0:
        raise ValueError(f"{name} must be in [0, 500], got {v}")
    return v


def _check_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {type(value).__name__}")
    return float(value)


def _validate_buckets(buckets: tuple[RatingBaseline, ...]) -> None:
    labels = {b.bucket_label for b in buckets}
    if labels != set(_ALLOWED_BUCKET_LABELS):
        missing = set(_ALLOWED_BUCKET_LABELS) - labels
        extra = labels - set(_ALLOWED_BUCKET_LABELS)
        raise ValueError(
            f"buckets must cover {_ALLOWED_BUCKET_LABELS!r}; "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )


__all__ = [
    "BASELINES_PATH",
    "RatingBaseline",
    "RatingBaselines",
    "get_baselines",
    "reset_cache",
]
