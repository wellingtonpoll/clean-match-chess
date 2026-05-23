"""Plain-language narrative builder (T088, FR-012).

Builds a `Narrative` from an `AuditRun` + `SuspicionScore`. Per-language
templates produce a summary paragraph plus zero or more flagged-segment
records when the risk level rises to MEDIUM / HIGH.

The output is checked by the lexical audit before any artefact is
written — see `bundle.py`.
"""

from __future__ import annotations

from typing import Final

from shared_types.audit_run import AuditRun
from shared_types.report import FlaggedSegment, Narrative
from shared_types.score import RiskLevel, SuspicionScore
from shared_types.signal import Regime, Segment

_SUMMARY_TEMPLATES_EN: Final[dict[RiskLevel, str]] = {
    RiskLevel.LOW: (
        "The probabilistic assessment of this game yields a {score:.2f} score "
        "(LOW risk; 95% CI {ci_low:.2f} to {ci_high:.2f}). The dominant signals "
        "were {signals}. No segment exceeded the elevated-risk threshold. This "
        "is a probabilistic assessment, not an accusation."
    ),
    RiskLevel.MEDIUM: (
        "The probabilistic assessment of this game yields a {score:.2f} score "
        "(MEDIUM risk; 95% CI {ci_low:.2f} to {ci_high:.2f}). The dominant "
        "signals were {signals}. One or more segments warrant human review. "
        "This is a probabilistic assessment, not an accusation."
    ),
    RiskLevel.HIGH: (
        "The probabilistic assessment of this game yields a {score:.2f} score "
        "(HIGH risk; 95% CI {ci_low:.2f} to {ci_high:.2f}). The dominant "
        "signals were {signals}. Multiple segments showed patterns consistent "
        "with engine consultation in difficult positions. This is a "
        "probabilistic assessment, not an accusation, and warrants human review."
    ),
}

_SUMMARY_TEMPLATES_PT: Final[dict[RiskLevel, str]] = {
    RiskLevel.LOW: (
        "A análise probabilística desta partida retorna pontuação {score:.2f} "
        "(risco BAIXO; IC 95% {ci_low:.2f} a {ci_high:.2f}). Sinais dominantes: "
        "{signals}. Nenhum segmento ultrapassou o limiar de risco elevado. "
        "Esta é uma avaliação probabilística, não uma alegação."
    ),
    RiskLevel.MEDIUM: (
        "A análise probabilística desta partida retorna pontuação {score:.2f} "
        "(risco MÉDIO; IC 95% {ci_low:.2f} a {ci_high:.2f}). Sinais dominantes: "
        "{signals}. Um ou mais segmentos merecem revisão humana. Esta é uma "
        "avaliação probabilística, não uma alegação."
    ),
    RiskLevel.HIGH: (
        "A análise probabilística desta partida retorna pontuação {score:.2f} "
        "(risco ALTO; IC 95% {ci_low:.2f} a {ci_high:.2f}). Sinais dominantes: "
        "{signals}. Múltiplos segmentos mostraram padrões consistentes com "
        "consulta a engine em posições difíceis. Esta é uma avaliação "
        "probabilística, não uma alegação, e merece revisão humana."
    ),
}


def build_narrative(
    run: AuditRun,  # noqa: ARG001
    score: SuspicionScore,
    segments: tuple[Segment, ...],
    *,
    language: str = "en",
) -> Narrative:
    paragraph = _summary_paragraph(score, language=language)
    flagged = _flag_segments(score, segments)
    return Narrative(
        summary_paragraph=paragraph,
        flagged_segments=flagged,
        forbidden_terms_clean=True,
    )


def _summary_paragraph(score: SuspicionScore, *, language: str) -> str:
    templates = _SUMMARY_TEMPLATES_EN if language == "en" else _SUMMARY_TEMPLATES_PT
    template = templates[score.risk_level]
    signals = (
        ", ".join(score.dominant_signals)
        if score.dominant_signals
        else (
            "no signal carried meaningful weight"
            if language == "en"
            else "nenhum sinal teve peso relevante"
        )
    )
    return template.format(
        score=score.score,
        ci_low=score.confidence_interval[0],
        ci_high=score.confidence_interval[1],
        signals=signals,
    )


def _flag_segments(
    score: SuspicionScore, segments: tuple[Segment, ...]
) -> tuple[FlaggedSegment, ...]:
    if score.risk_level is RiskLevel.LOW:
        return ()
    out: list[FlaggedSegment] = []
    for seg in segments:
        if seg.score_contribution < 0.5 and seg.regime is not Regime.ENGINE_LIKE:
            continue
        evidence = (
            f"Phase {seg.phase.value} from ply {seg.ply_range[0]} to {seg.ply_range[1]}",
            f"Aggregated signals: {len(seg.signals)} measurements",
            "Principle 7: complexity-weighted contribution",
        )
        out.append(
            FlaggedSegment(
                segment=seg,
                headline=(
                    f"Segment {seg.phase.value} marked for review (regime: {seg.regime.value})."
                ),
                evidence=evidence,
            )
        )
    return tuple(out)
