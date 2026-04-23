"""Command-line entry point for claude-skill-check."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from claude_skill_check import __version__
from claude_skill_check.validator import (
    Severity,
    ValidationResult,
    validate_paths,
)


def _format_human(results: list[ValidationResult]) -> str:
    lines: list[str] = []
    total_errors = 0
    total_warnings = 0
    for r in results:
        if not r.issues:
            lines.append(f"OK  {r.path}")
            continue
        lines.append(f"{r.path}:")
        for i in r.issues:
            lines.append(f"  {i.severity.value:7s} {i.code} {i.message}")
            if i.severity is Severity.ERROR:
                total_errors += 1
            else:
                total_warnings += 1
    lines.append("")
    lines.append(
        f"{len(results)} file(s), {total_errors} error(s), {total_warnings} warning(s)"
    )
    return "\n".join(lines)


def _collect_paths(inputs: Sequence[str]) -> list[Path]:
    out: list[Path] = []
    for item in inputs:
        p = Path(item)
        if p.is_dir():
            out.extend(sorted(p.rglob("SKILL.md")))
        else:
            out.append(p)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="claude-skill-check",
        description="Lint Claude Code SKILL.md files.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Skill file paths (or directories — scanned for SKILL.md recursively)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only print errors; hide OK lines and warnings",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"claude-skill-check {__version__}",
    )
    args = parser.parse_args(argv)

    paths = _collect_paths(args.paths)
    if not paths:
        print("no SKILL.md files found", file=sys.stderr)
        return 2

    results = validate_paths(paths)

    if args.quiet:
        filtered: list[ValidationResult] = []
        for r in results:
            if r.errors:
                filtered.append(
                    ValidationResult(path=r.path, issues=list(r.errors))
                )
        output = _format_human(filtered) if filtered else ""
        if output:
            print(output)
    else:
        print(_format_human(results))

    exit_code = 0 if all(r.ok for r in results) else 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
