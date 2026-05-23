"""`design_system audit-replay` integration (T079).

Replays a reproducibility manifest against the current design-system
version. The exit-code matrix is locked by
`specs/002-design-system/contracts/manifest-field.md`:
- 0 → version match (or warn-only mismatch)
- 1 → audit failure
- 2 → manifest missing / unparseable
- 3 → internal bug
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest
from design_system.__main__ import main
from design_system.version import __version__


def _manifest_payload(design_system_version: str | None) -> dict[str, object]:
    payload: dict[str, object] = {
        "engine_name": "stockfish",
        "engine_version": "16.1",
        "engine_binary_sha256": "0" * 64,
        "engine_uci_options": {"Threads": 1, "Hash": 16},
        "heuristics": [],
        "analysis_core_version": "0.1.0",
        "report_engine_version": "0.1.0",
        "python_chess_version": "1.999",
        "opening_book_sha256": "0" * 64,
        "input_pgn_sha256": "0" * 64,
        "started_at": "2026-01-01T00:00:00",
        "host": {"os": "linux", "arch": "x86_64", "cpu_model": "x", "ram_bytes": 0},
    }
    if design_system_version is not None:
        payload["design_system_version"] = design_system_version
    return payload


def _write_manifest(tmp_path: Path, design_system_version: str | None) -> Path:
    target = tmp_path / "manifest.json"
    target.write_text(json.dumps(_manifest_payload(design_system_version)))
    return target


def test_replay_passes_when_version_matches(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write_manifest(tmp_path, __version__)
    rc = main(["audit-replay", str(path)])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["status"] == "pass"
    assert payload["design_system_version"] == __version__


def test_replay_warns_on_version_drift(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_manifest(tmp_path, "0.0.1")
    rc = main(["audit-replay", str(path)])
    assert rc == 0  # drift is warn-only, not a hard fail
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["status"] == "pass"
    rules = {f["rule"] for f in payload["findings"]}
    assert "design_system_version_drift" in rules


def test_replay_warns_on_missing_field(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_manifest(tmp_path, None)
    rc = main(["audit-replay", str(path)])
    assert rc == 0  # missing field is warn-only
    out = capsys.readouterr().out
    payload = json.loads(out)
    rules = {f["rule"] for f in payload["findings"]}
    assert "manifest_missing_design_system_version" in rules


def test_replay_exits_2_when_manifest_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "nope.json"
    rc = main(["audit-replay", str(missing)])
    assert rc == 2


def test_replay_exits_2_when_manifest_unparseable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json")
    rc = main(["audit-replay", str(bad)])
    assert rc == 2


def test_replay_exits_2_when_version_field_unparseable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write_manifest(tmp_path, "not-a-semver")
    rc = main(["audit-replay", str(path)])
    assert rc == 2


def test_replay_without_argv_prints_usage(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["audit-replay"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "usage" in err.lower()


def test_replay_handles_string_argv_via_io(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Smoke test: main() reads from a sequence argv list directly."""
    path = _write_manifest(tmp_path, __version__)
    buf = StringIO()
    rc = main(["audit-replay", str(path)])
    assert rc == 0
    _ = buf  # no-op; ensures import doesn't drift
