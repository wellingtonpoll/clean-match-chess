"""LockedUciOptions enforces determinism constraints."""

from __future__ import annotations

import pytest
from analysis_core.engine.uci import (
    DEFAULT_DEPTH,
    DEFAULT_HASH_MB,
    DEFAULT_MULTIPV,
    LockedUciOptions,
)


def test_defaults_match_research() -> None:
    opts = LockedUciOptions()
    assert opts.depth == DEFAULT_DEPTH
    assert opts.threads == 1
    assert opts.hash_mb == DEFAULT_HASH_MB
    assert opts.multipv == DEFAULT_MULTIPV
    assert opts.use_nnue is True


def test_threads_must_be_one() -> None:
    with pytest.raises(ValueError, match="threads"):
        LockedUciOptions(threads=4)


def test_depth_must_be_positive() -> None:
    with pytest.raises(ValueError, match="depth"):
        LockedUciOptions(depth=0)


def test_hash_floor() -> None:
    with pytest.raises(ValueError, match="hash_mb"):
        LockedUciOptions(hash_mb=8)


def test_multipv_floor() -> None:
    with pytest.raises(ValueError, match="multipv"):
        LockedUciOptions(multipv=0)


def test_as_uci_dict_contract() -> None:
    opts = LockedUciOptions()
    assert opts.as_uci_dict() == {
        "Threads": 1,
        "Hash": 256,
        "MultiPV": 5,
        "UseNNUE": True,
    }
