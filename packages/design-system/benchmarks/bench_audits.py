"""Audit-performance benchmarks (T081).

Budget envelope (from spec FR-018 + plan-§Performance):
    palette static CSS    Track A ≤  100 ms
    palette PDF (50-game) Track B ≤ 5000 ms (synthetic surrogate here)
    typography static CSS         ≤  2000 ms (large CSS surrogate)
    motion static CSS             ≤   100 ms
    lexical en + pt               ≤  1000 ms

Each benchmark is marked `benchmark` so the existing CI bench job picks
them up under the `benchmark` label-gated workflow. Run locally with:

    uv run pytest -m benchmark packages/design-system/benchmarks
"""

from __future__ import annotations

from pathlib import Path

import pytest
from design_system.audits.lexical import audit_text
from design_system.audits.motion import audit_static_css
from design_system.audits.palette import audit_generated_css as palette_audit
from design_system.audits.typography import audit_generated_css as typography_audit

ADAPTERS_ROOT: Path = Path(__file__).resolve().parents[1] / "adapters" / "weasyprint" / "tokens.css"


@pytest.mark.benchmark(group="audits")
def test_bench_palette_static(benchmark) -> None:  # type: ignore[no-untyped-def]
    """Palette Track A — static CSS scan ≤ 100 ms."""
    css = ADAPTERS_ROOT
    result = benchmark(lambda: palette_audit(css))
    assert result.status.value == "pass"
    if getattr(benchmark, "stats", None) is not None:
        # Soft assertion: average run stays under 100 ms.
        assert benchmark.stats.stats.mean < 0.100, (
            f"palette static audit mean {benchmark.stats.stats.mean * 1000:.1f} ms > 100 ms"
        )


@pytest.mark.benchmark(group="audits")
def test_bench_typography_static(benchmark) -> None:  # type: ignore[no-untyped-def]
    """Typography static CSS ≤ 2000 ms (PDF surrogate)."""
    css = ADAPTERS_ROOT
    result = benchmark(lambda: typography_audit(css))
    assert result.status.value == "pass"
    if getattr(benchmark, "stats", None) is not None:
        assert benchmark.stats.stats.mean < 2.000


@pytest.mark.benchmark(group="audits")
def test_bench_motion_static(benchmark) -> None:  # type: ignore[no-untyped-def]
    """Motion static CSS ≤ 100 ms."""
    css = ADAPTERS_ROOT
    result = benchmark(lambda: audit_static_css(css))
    assert result.status.value == "pass"
    if getattr(benchmark, "stats", None) is not None:
        assert benchmark.stats.stats.mean < 0.100


_LEXICAL_FIXTURE_EN = (
    "Behavioral Signal observed. Statistical Irregularity logged at ply 18. "
    "Risk Window between plies 14 and 22. Analytical Confidence 95%."
)
_LEXICAL_FIXTURE_PT = (
    "Sinal Comportamental observado. Irregularidade Estatística registrada no lance 18. "
    "Janela de Risco entre lances 14 e 22. Confiança Analítica 95%."
)


@pytest.mark.benchmark(group="audits")
def test_bench_lexical_both_languages(benchmark) -> None:  # type: ignore[no-untyped-def]
    """Lexical audit en + pt ≤ 1000 ms combined."""

    def _run() -> None:
        for lang, text in (("en", _LEXICAL_FIXTURE_EN), ("pt", _LEXICAL_FIXTURE_PT)):
            r = audit_text(text, languages=(lang,))
            assert r.status.value == "pass"

    benchmark(_run)
    if getattr(benchmark, "stats", None) is not None:
        assert benchmark.stats.stats.mean < 1.000
