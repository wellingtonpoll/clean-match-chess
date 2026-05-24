"""FPR-gate orchestrator (feature 005 T017).

Iterates a corpus root, runs the audit pipeline against every fixture
(reusing per-fixture cache when present), classifies each result as
TP/FP/TN/FN against the provenance label, and returns an ``FprGateReport``
matching ``specs/005-scoring-v2-phase2/contracts/fpr_gate.contract.md``.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path
from typing import Final

from analysis_core.ingest.pgn_loader import load_pgn_path
from analysis_core.pipeline.run import run_single_game
from pydantic import BaseModel, ConfigDict, Field
from shared_types.audit_run import AuditRun
from shared_types.game import PlayerColor
from shared_types.score import RISK_HIGH_MIN

from tests.fpr_gate.cache import load_cached, save_cached
from tests.fpr_gate.provenance import ProvenanceRecord, iter_corpus

DEFAULT_FPR_THRESHOLD: Final[float] = 0.020
DEFAULT_TPR_THRESHOLD: Final[float] = 0.800
DEFAULT_SCORE_DECISION_THRESHOLD: Final[float] = RISK_HIGH_MIN


class FixtureOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    fixture: str
    score: float
    label: str
    classification: str


class FprGateReport(BaseModel):
    """Structured output of a single gate run (contracts/fpr_gate.contract.md)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    passed: bool
    fpr: float
    fpr_threshold: float
    fpr_ci_95: tuple[float, float]
    tpr: float
    tpr_threshold: float
    tpr_ci_95: tuple[float, float]
    clean_corpus_size: int
    engine_assisted_corpus_size: int
    score_decision_threshold: float
    false_positives: tuple[FixtureOutcome, ...] = Field(default_factory=tuple)
    false_negatives: tuple[FixtureOutcome, ...] = Field(default_factory=tuple)
    thresholds_version: str

    def format_diagnostic(self) -> str:
        """Render the human-readable diagnostic per contract section Output."""
        n_clean = self.clean_corpus_size
        n_fp = len(self.false_positives)
        n_ea = self.engine_assisted_corpus_size
        n_tp = n_ea - len(self.false_negatives)
        fpr_lo, fpr_hi = self.fpr_ci_95
        tpr_lo, tpr_hi = self.tpr_ci_95
        lines = [
            f"FPR gate {'PASSED' if self.passed else 'FAILED'}:",
            (
                f"  clean corpus:    FPR = {self.fpr * 100:.1f}% "
                f"({n_fp}/{n_clean}), threshold <= {self.fpr_threshold * 100:.1f}% "
                f"[95% CI: {fpr_lo * 100:.1f}%-{fpr_hi * 100:.1f}%]"
            ),
            (
                f"  engine-assisted: TPR = {self.tpr * 100:.1f}% "
                f"({n_tp}/{n_ea}), threshold >= {self.tpr_threshold * 100:.1f}% "
                f"[95% CI: {tpr_lo * 100:.1f}%-{tpr_hi * 100:.1f}%]"
            ),
        ]
        if self.false_positives:
            lines.append("")
            lines.append("False positives (clean games flagged as suspect):")
            for fp in self.false_positives:
                lines.append(f"  - {fp.fixture}  (score={fp.score:.3f})")
        if self.false_negatives:
            lines.append("")
            lines.append("False negatives (engine-assisted games missed):")
            for fn in self.false_negatives:
                lines.append(f"  - {fn.fixture}  (score={fn.score:.3f})")
        return "\n".join(lines)


def wilson_score_interval(successes: int, trials: int, *, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval (closed-form, no scipy dependency).

    Returns (0.0, 1.0) when ``trials == 0``.
    """
    if trials == 0:
        return (0.0, 1.0)
    p_hat = successes / trials
    denom = 1.0 + z * z / trials
    center = (p_hat + z * z / (2 * trials)) / denom
    half = (z / denom) * math.sqrt(p_hat * (1 - p_hat) / trials + z * z / (4 * trials * trials))
    return (max(0.0, center - half), min(1.0, center + half))


# Default audit callback: full real pipeline. Tests inject stubs.
def _default_audit(pgn_path: Path) -> AuditRun:
    game = load_pgn_path(pgn_path)
    subject = PlayerColor.WHITE if game.players[0].subject else PlayerColor.BLACK
    return run_single_game(game, subject=subject)


def run_gate(
    corpus_root: Path,
    *,
    fpr_threshold: float = DEFAULT_FPR_THRESHOLD,
    tpr_threshold: float = DEFAULT_TPR_THRESHOLD,
    score_decision_threshold: float = DEFAULT_SCORE_DECISION_THRESHOLD,
    thresholds_version: str = "2.0.0",
    audit_callback: Callable[[Path], AuditRun] = _default_audit,
    expected_engine_sha256: str | None = None,
    expected_book_sha256: str | None = None,
    use_cache: bool = True,
) -> FprGateReport:
    """Run the FPR gate against a corpus and return a report.

    ``audit_callback`` is injectable for unit tests (mock the heavy pipeline).
    When ``use_cache`` is True and ``expected_*_sha256`` are provided,
    per-fixture cache is consulted before invoking the callback.
    """
    clean: list[tuple[Path, AuditRun]] = []
    engine_assisted: list[tuple[Path, AuditRun]] = []

    for pgn_path, provenance in iter_corpus(corpus_root):
        run = _resolve_run(
            pgn_path,
            provenance,
            corpus_root=corpus_root,
            audit_callback=audit_callback,
            expected_engine_sha256=expected_engine_sha256,
            expected_book_sha256=expected_book_sha256,
            use_cache=use_cache,
        )
        bucket = clean if provenance.label == "clean" else engine_assisted
        bucket.append((pgn_path, run))

    false_positives = _classify_misses(
        clean,
        target_label="clean",
        threshold=score_decision_threshold,
        miss_when_above=True,
    )
    false_negatives = _classify_misses(
        engine_assisted,
        target_label="engine_assisted",
        threshold=score_decision_threshold,
        miss_when_above=False,
    )

    n_clean = len(clean)
    n_ea = len(engine_assisted)
    fpr = len(false_positives) / n_clean if n_clean else 0.0
    tpr = (n_ea - len(false_negatives)) / n_ea if n_ea else 0.0

    return FprGateReport(
        passed=fpr <= fpr_threshold and tpr >= tpr_threshold,
        fpr=fpr,
        fpr_threshold=fpr_threshold,
        fpr_ci_95=wilson_score_interval(len(false_positives), n_clean),
        tpr=tpr,
        tpr_threshold=tpr_threshold,
        tpr_ci_95=wilson_score_interval(n_ea - len(false_negatives), n_ea),
        clean_corpus_size=n_clean,
        engine_assisted_corpus_size=n_ea,
        score_decision_threshold=score_decision_threshold,
        false_positives=tuple(false_positives),
        false_negatives=tuple(false_negatives),
        thresholds_version=thresholds_version,
    )


def _resolve_run(
    pgn_path: Path,
    provenance: ProvenanceRecord,
    *,
    corpus_root: Path,
    audit_callback: Callable[[Path], AuditRun],
    expected_engine_sha256: str | None,
    expected_book_sha256: str | None,
    use_cache: bool,
) -> AuditRun:
    if use_cache and expected_engine_sha256 and expected_book_sha256:
        cached = load_cached(
            pgn_path,
            corpus_root=corpus_root,
            expected_engine_sha256=expected_engine_sha256,
            expected_book_sha256=expected_book_sha256,
        )
        if cached is not None:
            return cached
    run = audit_callback(pgn_path)
    if use_cache and run.manifest is not None:
        save_cached(pgn_path, run, corpus_root=corpus_root)
    _ = provenance  # provenance is consumed by the caller for labeling
    return run


def _classify_misses(
    items: list[tuple[Path, AuditRun]],
    *,
    target_label: str,
    threshold: float,
    miss_when_above: bool,
) -> list[FixtureOutcome]:
    """Return the FixtureOutcomes that are misses (FPs for clean, FNs for engine_assisted)."""
    misses: list[FixtureOutcome] = []
    for path, run in items:
        score = run.score.score if run.score is not None else 0.0
        flagged = score >= threshold
        is_miss = flagged if miss_when_above else not flagged
        if is_miss:
            misses.append(
                FixtureOutcome(
                    fixture=str(path),
                    score=score,
                    label=target_label,
                    classification="false_positive" if miss_when_above else "false_negative",
                )
            )
    return misses
