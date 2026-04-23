"""Core validation logic for Claude Code SKILL.md files.

A skill file is a Markdown document with a YAML frontmatter block delimited
by `---` on the first line and a closing `---`. The frontmatter declares
fields like `name`, `description`, and optional `allowed-tools` / `model`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable

import yaml

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)

REQUIRED_FIELDS = ("name", "description")
OPTIONAL_FIELDS = ("allowed-tools", "model", "argument-hint")

NAME_RE = re.compile(r"^[a-z][a-z0-9\-]{0,62}[a-z0-9]$")
MIN_DESCRIPTION_LEN = 20
MAX_DESCRIPTION_LEN = 1024

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("anthropic API key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("OpenAI API key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("generic PEM block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Issue:
    severity: Severity
    code: str
    message: str
    line: int | None = None


@dataclass
class ValidationResult:
    path: str
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.severity is Severity.ERROR for i in self.issues)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.WARNING]


def _err(code: str, msg: str, line: int | None = None) -> Issue:
    return Issue(Severity.ERROR, code, msg, line)


def _warn(code: str, msg: str, line: int | None = None) -> Issue:
    return Issue(Severity.WARNING, code, msg, line)


def _find_line(source: str, needle: str) -> int | None:
    for idx, line in enumerate(source.splitlines(), start=1):
        if needle in line:
            return idx
    return None


def validate_skill_source(source: str, path: str = "<string>") -> ValidationResult:
    """Validate a SKILL.md document given its raw text content."""
    result = ValidationResult(path=path)

    if not source.strip():
        result.issues.append(_err("E001", "file is empty"))
        return result

    match = FRONTMATTER_RE.match(source)
    if not match:
        result.issues.append(
            _err(
                "E002",
                "missing YAML frontmatter (expected '---' fence on first line)",
                line=1,
            )
        )
        return result

    frontmatter_text = match.group(1)
    try:
        data = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        result.issues.append(_err("E003", f"frontmatter is not valid YAML: {exc}"))
        return result

    if data is None:
        result.issues.append(_err("E004", "frontmatter is empty"))
        return result

    if not isinstance(data, dict):
        result.issues.append(
            _err("E005", f"frontmatter must be a mapping, got {type(data).__name__}")
        )
        return result

    for req in REQUIRED_FIELDS:
        if req not in data:
            result.issues.append(_err("E100", f"missing required field '{req}'"))

    if "name" in data:
        name = data["name"]
        if not isinstance(name, str):
            result.issues.append(
                _err("E101", "'name' must be a string", line=_find_line(source, "name:"))
            )
        elif not NAME_RE.match(name):
            result.issues.append(
                _err(
                    "E102",
                    "'name' must be lowercase kebab-case (e.g. 'my-skill'), "
                    "1-64 chars, starting with a letter",
                    line=_find_line(source, "name:"),
                )
            )

    if "description" in data:
        desc = data["description"]
        if not isinstance(desc, str):
            result.issues.append(
                _err(
                    "E110",
                    "'description' must be a string",
                    line=_find_line(source, "description:"),
                )
            )
        else:
            n = len(desc.strip())
            if n < MIN_DESCRIPTION_LEN:
                result.issues.append(
                    _warn(
                        "W111",
                        f"'description' is too short ({n} chars); "
                        f"aim for at least {MIN_DESCRIPTION_LEN}",
                    )
                )
            if n > MAX_DESCRIPTION_LEN:
                result.issues.append(
                    _err(
                        "E112",
                        f"'description' is too long ({n} chars); "
                        f"keep under {MAX_DESCRIPTION_LEN}",
                    )
                )

    if "allowed-tools" in data:
        tools = data["allowed-tools"]
        if not isinstance(tools, (list, str)):
            result.issues.append(
                _err("E120", "'allowed-tools' must be a string or list of strings")
            )
        elif isinstance(tools, list):
            for i, t in enumerate(tools):
                if not isinstance(t, str):
                    result.issues.append(
                        _err("E121", f"'allowed-tools[{i}]' must be a string")
                    )

    known = set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)
    for key in data.keys():
        if key not in known:
            result.issues.append(_warn("W900", f"unknown field '{key}' in frontmatter"))

    for label, pat in SECRET_PATTERNS:
        if pat.search(source):
            result.issues.append(
                _err("E200", f"possible {label} leaked in skill file")
            )

    body = source[match.end():].strip()
    if not body:
        result.issues.append(_warn("W300", "skill body is empty after frontmatter"))

    return result


def validate_skill_file(path: str | Path) -> ValidationResult:
    """Validate a SKILL.md file on disk."""
    p = Path(path)
    if not p.exists():
        r = ValidationResult(path=str(p))
        r.issues.append(_err("E000", f"file not found: {p}"))
        return r
    if not p.is_file():
        r = ValidationResult(path=str(p))
        r.issues.append(_err("E000", f"not a regular file: {p}"))
        return r
    try:
        source = p.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        r = ValidationResult(path=str(p))
        r.issues.append(_err("E001", f"file is not valid UTF-8: {exc}"))
        return r
    return validate_skill_source(source, path=str(p))


def validate_paths(paths: Iterable[str | Path]) -> list[ValidationResult]:
    """Validate multiple skill files and return a list of results."""
    return [validate_skill_file(p) for p in paths]
