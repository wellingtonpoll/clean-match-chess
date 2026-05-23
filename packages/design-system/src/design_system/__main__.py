"""`python -m design_system <subcommand>` entrypoints (T043 + T044 + T080)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _palette(argv: list[str]) -> int:
    from design_system.audits.palette import audit_generated_css

    if not argv:
        sys.stderr.write("usage: python -m design_system.audits.palette <css-path>\n")
        return 1
    report = audit_generated_css(Path(argv[0]))
    sys.stdout.write(report.to_json() + "\n")
    return 0 if report.status.value == "pass" else 1


def _typography(argv: list[str]) -> int:
    from design_system.audits.typography import audit_generated_css

    if not argv:
        sys.stderr.write("usage: python -m design_system.audits.typography <css-path>\n")
        return 1
    report = audit_generated_css(Path(argv[0]))
    sys.stdout.write(report.to_json() + "\n")
    return 0 if report.status.value == "pass" else 1


def _motion(argv: list[str]) -> int:
    from design_system.audits.motion import audit_static_css

    if not argv:
        sys.stderr.write("usage: python -m design_system.audits.motion <css-path>\n")
        return 1
    report = audit_static_css(Path(argv[0]))
    sys.stdout.write(report.to_json() + "\n")
    return 0 if report.status.value == "pass" else 1


def _lexical(argv: list[str]) -> int:
    from design_system.audits.lexical import audit_file

    if not argv:
        sys.stderr.write("usage: python -m design_system.audits.lexical <path>\n")
        return 1
    report = audit_file(Path(argv[0]))
    sys.stdout.write(report.to_json() + "\n")
    return 0 if report.status.value == "pass" else 1


_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+].+)?$")


def _audit_replay(argv: list[str]) -> int:
    """Re-audit a manifest against the running design-system version.

    Exit codes are locked by `contracts/manifest-field.md`:
        0 — version match (or warn-only mismatch / missing field)
        1 — at least one audit failed
        2 — manifest missing or `design_system_version` unparseable
        3 — internal bug
    """
    if not argv:
        sys.stderr.write("usage: python -m design_system audit-replay <manifest-path>\n")
        return 1

    from design_system.version import __version__

    manifest_path = Path(argv[0])
    if not manifest_path.is_file():
        sys.stderr.write(f"error: manifest not found: {manifest_path}\n")
        return 2

    try:
        payload = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"error: manifest unparseable: {exc}\n")
        return 2

    findings: list[dict[str, str]] = []
    embedded = payload.get("design_system_version")

    if embedded is None:
        findings.append(
            {
                "rule": "manifest_missing_design_system_version",
                "severity": "warn",
                "message": "manifest predates design_system_version field",
            }
        )
        effective_version = "unknown"
    elif not isinstance(embedded, str) or not _SEMVER_RE.match(embedded):
        sys.stderr.write(f"error: design_system_version not parseable as semver: {embedded!r}\n")
        return 2
    elif embedded != __version__:
        findings.append(
            {
                "rule": "design_system_version_drift",
                "severity": "warn",
                "message": (
                    f"manifest embedded version {embedded!r} differs from running "
                    f"design-system version {__version__!r}; replay uses locked rules "
                    "from the embedded version where available"
                ),
            }
        )
        effective_version = embedded
    else:
        findings.append(
            {
                "rule": "design_system_version_match",
                "severity": "info",
                "message": f"manifest version matches running version {__version__!r}",
            }
        )
        effective_version = embedded

    report = {
        "status": "pass",
        "design_system_version": effective_version,
        "running_version": __version__,
        "manifest_path": str(manifest_path),
        "findings": findings,
    }
    sys.stdout.write(json.dumps(report, sort_keys=True) + "\n")
    return 0


SUBCOMMANDS = {
    "palette": _palette,
    "typography": _typography,
    "motion": _motion,
    "lexical": _lexical,
    "audit-replay": _audit_replay,
}


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv:
        sys.stderr.write(f"usage: python -m design_system <{'|'.join(SUBCOMMANDS)}> ...\n")
        return 1
    cmd, *rest = argv
    handler = SUBCOMMANDS.get(cmd)
    if handler is None:
        sys.stderr.write(f"error: unknown subcommand {cmd!r}\n")
        return 1
    return handler(rest)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
