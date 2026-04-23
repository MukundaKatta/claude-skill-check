"""Linter for Claude Code SKILL.md files."""

from claude_skill_check.validator import (
    Issue,
    Severity,
    ValidationResult,
    validate_skill_file,
    validate_skill_source,
)

__all__ = [
    "Issue",
    "Severity",
    "ValidationResult",
    "validate_skill_file",
    "validate_skill_source",
]

__version__ = "0.1.0"
