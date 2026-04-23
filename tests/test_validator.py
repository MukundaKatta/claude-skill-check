"""Tests for the claude-skill-check validator."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from claude_skill_check.validator import (
    Severity,
    validate_skill_file,
    validate_skill_source,
)


def _codes(issues) -> list[str]:
    return [i.code for i in issues]


def test_valid_minimal_skill() -> None:
    source = textwrap.dedent(
        """\
        ---
        name: my-skill
        description: A valid skill description that is long enough to pass.
        ---

        # My skill

        Body goes here.
        """
    )
    result = validate_skill_source(source)
    assert result.ok
    assert result.errors == []


def test_missing_frontmatter() -> None:
    result = validate_skill_source("just a body with no frontmatter")
    assert not result.ok
    assert "E002" in _codes(result.errors)


def test_empty_file() -> None:
    result = validate_skill_source("")
    assert not result.ok
    assert "E001" in _codes(result.errors)


def test_missing_required_fields() -> None:
    source = "---\nfoo: bar\n---\n"
    result = validate_skill_source(source)
    codes = _codes(result.errors)
    assert "E100" in codes
    assert sum(1 for c in codes if c == "E100") == 2


def test_invalid_name_uppercase() -> None:
    source = textwrap.dedent(
        """\
        ---
        name: MySkill
        description: A long enough description for this test to pass validation.
        ---
        body
        """
    )
    result = validate_skill_source(source)
    assert "E102" in _codes(result.errors)


def test_short_description_warns() -> None:
    source = textwrap.dedent(
        """\
        ---
        name: short-desc
        description: too short
        ---
        body
        """
    )
    result = validate_skill_source(source)
    assert result.ok
    assert "W111" in _codes(result.warnings)


def test_secret_leak_detected() -> None:
    source = textwrap.dedent(
        """\
        ---
        name: leaky
        description: A description long enough to pass the minimum length check.
        ---

        Here is my key: sk-ant-api03_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_xyz
        """
    )
    result = validate_skill_source(source)
    assert not result.ok
    assert "E200" in _codes(result.errors)


def test_unknown_field_warns() -> None:
    source = textwrap.dedent(
        """\
        ---
        name: has-extra
        description: A description long enough to pass the minimum length check.
        extra_junk: hello
        ---
        body
        """
    )
    result = validate_skill_source(source)
    assert result.ok
    assert "W900" in _codes(result.warnings)


def test_empty_body_warns() -> None:
    source = textwrap.dedent(
        """\
        ---
        name: empty-body
        description: A description long enough to pass the minimum length check.
        ---
        """
    )
    result = validate_skill_source(source)
    assert "W300" in _codes(result.warnings)


def test_frontmatter_must_be_mapping() -> None:
    source = "---\n- 1\n- 2\n---\nbody"
    result = validate_skill_source(source)
    assert "E005" in _codes(result.errors)


def test_broken_yaml() -> None:
    source = "---\nname: [unclosed\n---\nbody"
    result = validate_skill_source(source)
    assert "E003" in _codes(result.errors)


def test_validate_skill_file_missing(tmp_path: Path) -> None:
    missing = tmp_path / "nope.md"
    result = validate_skill_file(missing)
    assert "E000" in _codes(result.errors)


def test_validate_skill_file_roundtrip(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        textwrap.dedent(
            """\
            ---
            name: from-disk
            description: A description long enough to pass the minimum length check.
            ---
            body
            """
        )
    )
    result = validate_skill_file(skill)
    assert result.ok
    assert result.path == str(skill)


def test_allowed_tools_string_ok() -> None:
    source = textwrap.dedent(
        """\
        ---
        name: tools-as-string
        description: A description long enough to pass the minimum length check.
        allowed-tools: Read, Edit
        ---
        body
        """
    )
    result = validate_skill_source(source)
    assert result.ok


def test_allowed_tools_list_items_must_be_strings() -> None:
    source = textwrap.dedent(
        """\
        ---
        name: tools-list
        description: A description long enough to pass the minimum length check.
        allowed-tools:
          - Read
          - 42
        ---
        body
        """
    )
    result = validate_skill_source(source)
    assert "E121" in _codes(result.errors)


def test_severity_counts_on_result() -> None:
    source = "---\nfoo: bar\n---\n"
    result = validate_skill_source(source)
    assert all(i.severity is Severity.ERROR for i in result.errors)
    assert all(i.severity is Severity.WARNING for i in result.warnings)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
