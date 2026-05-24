"""One-shot maintainer script — derive `rating_baselines.json` from Lichess open database.

Reproducible: pinned dataset month + deterministic seed. Output is the artifact
committed under `packages/heuristics/data/rating_baselines.json`; this script
is NOT invoked at audit time.

Methodology (per spec FR-011 + research.md R2):
  1. Download lichess_db_standard_rated_<MONTH>.pgn.zst from Lichess open DB.
  2. Filter games: both players Elo in [600, 3500], time control rapid/classical,
     ≥ 20 plies.
  3. Bin by lower-of-both-ratings into 6 rating buckets.
  4. Random-sample 5000 games per bucket (seeded RNG).
  5. Run Stockfish depth 12 over sampled games (cheap baseline — population stats).
  6. Compute per-bucket: mean+stdev of top-1 rate, weighted-top-1 rate, ACPL.
  7. Emit JSON conforming to contracts/rating_baselines.schema.json.

Runtime: ~6 hours on reference machine. Use --dry-run for code review without
the multi-GB dataset download.

Usage:
    python build_baselines.py [--dry-run] [--seed SEED] [--month YYYY-MM]
        [--output PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Pin a specific Lichess monthly export for reproducibility.
DEFAULT_MONTH = "2025-06"
DEFAULT_SEED = 0
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "rating_baselines.json"

BUCKET_DEFINITIONS: tuple[tuple[str, int | None, int | None], ...] = (
    ("≤1200", 1, 1200),
    ("1201-1500", 1201, 1500),
    ("1501-1800", 1501, 1800),
    ("1801-2100", 1801, 2100),
    ("2101-2400", 2101, 2400),
    ("2401+", 2401, 3500),
)

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

STUB_SAMPLE_SIZE = 0  # Marks the entry as a stub; real run sets to 5000+


def build_buckets_stub() -> list[dict[str, object]]:
    """Return the documented stub buckets (FR-011 fallback path)."""
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
    # Rating-unknown bucket — median of the 6 rated buckets.
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


def build_buckets_real(month: str, seed: int) -> list[dict[str, object]]:
    """Real-data path — download Lichess month, analyze, compute baselines.

    NOT IMPLEMENTED in Phase 1. Phase 2 fills this in. See research.md R2 for
    the full methodology. For Phase 1 use --dry-run (stub fallback acceptable
    per spec FR-011).
    """
    raise NotImplementedError(
        "Real-data baseline derivation not implemented in Phase 1. "
        "Use --dry-run to emit documented stub values. "
        "Phase 2 backlog item P2-T003 wires the real Lichess download path."
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate rating_baselines.json")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Emit hand-curated stub values (no dataset download). Phase 1 fallback.",
    )
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument(
        "--month", default=DEFAULT_MONTH, help="Lichess month export (YYYY-MM). Default: 2025-06."
    )
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args(argv)

    if args.dry_run:
        buckets = build_buckets_stub()
        source = "hand-curated-stub (Phase 1 fallback; lit. values, not measured)"
    else:
        buckets = build_buckets_real(args.month, args.seed)
        source = f"lichess-db-{args.month}"

    payload = {
        "version": "1.0.0",
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
