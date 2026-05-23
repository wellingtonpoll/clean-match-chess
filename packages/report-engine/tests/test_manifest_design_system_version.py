"""design_system_version stamp consistency (T049 + T053)."""

from __future__ import annotations

import json

from report_engine.bundle import write_bundle
from report_engine.styles import get_design_system_version


def test_bundle_manifest_carries_design_system_version(bundle, tmp_path) -> None:
    out = tmp_path / "case.zip"
    artefacts = write_bundle(bundle, out)
    payload = json.loads(artefacts.manifest_path.read_text())
    assert payload["design_system_version"]
    assert payload["design_system_version"] == bundle.manifest.design_system_version


def test_design_system_version_helper_matches_package_version() -> None:
    from design_system.version import __version__

    assert get_design_system_version() == __version__
