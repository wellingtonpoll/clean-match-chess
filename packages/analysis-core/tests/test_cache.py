"""Cache key derivation + hit/miss roundtrip."""

from __future__ import annotations

from pathlib import Path

from analysis_core.pipeline import cache


def test_cache_miss_then_hit(cleanmatch_home: Path, manifest_factory) -> None:
    m = manifest_factory()
    assert cache.is_cached(m) is False
    cache.persist_manifest(m)
    assert cache.is_cached(m) is True


def test_run_dir_changes_with_manifest_inputs(cleanmatch_home: Path, manifest_factory) -> None:
    a = manifest_factory(input_pgn_sha256="1" * 64)
    b = manifest_factory(input_pgn_sha256="2" * 64)
    assert cache.run_dir_for(a) != cache.run_dir_for(b)


def test_persist_and_reload(cleanmatch_home: Path, manifest_factory) -> None:
    m = manifest_factory()
    path = cache.persist_manifest(m)
    loaded = cache.load_manifest(path.parent)
    assert loaded.input_pgn_sha256 == m.input_pgn_sha256
    assert loaded.design_system_version == m.design_system_version


def test_cleanmatch_home_env_override(cleanmatch_home: Path) -> None:
    assert cache.cleanmatch_home() == cleanmatch_home
    assert cache.runs_dir() == cleanmatch_home / "runs"


def test_pool_config_validates() -> None:
    import pytest
    from analysis_core.engine.stockfish_pool import PoolConfig
    from analysis_core.engine.uci import LockedUciOptions

    with pytest.raises(ValueError):
        PoolConfig(binary_path="", workers=1, options=LockedUciOptions())
    with pytest.raises(ValueError):
        PoolConfig(binary_path="/usr/bin/stockfish", workers=0, options=LockedUciOptions())
