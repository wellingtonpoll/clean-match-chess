"""Cross-architecture tolerance placeholder (T083).

The CLI's determinism guarantee (FR-017) is bit-identical on the same
CPU architecture, with documented numerical tolerance across
architectures. CI runs on a single architecture, so this test is
skip-marked. It documents the tolerance contract and serves as the
hook for the cross-arch test rig once it exists.
"""

from __future__ import annotations

import pytest

EVAL_TOLERANCE_CP = 1
AGGREGATE_TOLERANCE = 0.001


@pytest.mark.skip(reason="cross-architecture rig deferred (FR-017 cross-arch case)")
def test_cross_arch_tolerance_documented() -> None:
    # Placeholder: once a cross-arch CI matrix exists, this test will
    # rerun the canonical audit on x86_64 and aarch64 + assert
    #   abs(score_a - score_b) <= AGGREGATE_TOLERANCE
    #   abs(eval_a - eval_b)   <= EVAL_TOLERANCE_CP
    raise AssertionError("must be exercised once the cross-arch rig lands")
