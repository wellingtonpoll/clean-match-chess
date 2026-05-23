"""`python -m design_system <subcommand>` entrypoints (T043 + T044)."""

from __future__ import annotations

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


def _audit_replay(argv: list[str]) -> int:
    if not argv:
        sys.stderr.write("usage: python -m design_system audit-replay <run-id>\n")
        return 1
    sys.stderr.write(
        "warning: audit-replay deferred. Use the individual audit subcommands "
        "or the report-engine's bundle workflow.\n"
    )
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
