"""Tests for the claude-skill-check validator.

These tests use only the Python standard library (``unittest``) so they run
with either ``python -m unittest discover -s tests`` or ``pytest`` without any
third-party test dependencies.
"""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from claude_skill_check.validator import (
    NAME_RE,
    Severity,
    validate_skill_file,
    validate_skill_source,
)


def _codes(issues) -> list[str]:
    return [i.code for i in issues]


class ValidateSourceTests(unittest.TestCase):
    def test_valid_minimal_skill(self) -> None:
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
        self.assertTrue(result.ok)
        self.assertEqual(result.errors, [])

    def test_missing_frontmatter(self) -> None:
        result = validate_skill_source("just a body with no frontmatter")
        self.assertFalse(result.ok)
        self.assertIn("E002", _codes(result.errors))

    def test_empty_file(self) -> None:
        result = validate_skill_source("")
        self.assertFalse(result.ok)
        self.assertIn("E001", _codes(result.errors))

    def test_whitespace_only_file(self) -> None:
        result = validate_skill_source("   \n\t\n")
        self.assertFalse(result.ok)
        self.assertIn("E001", _codes(result.errors))

    def test_missing_required_fields(self) -> None:
        source = "---\nfoo: bar\n---\n"
        result = validate_skill_source(source)
        codes = _codes(result.errors)
        self.assertIn("E100", codes)
        self.assertEqual(sum(1 for c in codes if c == "E100"), 2)

    def test_invalid_name_uppercase(self) -> None:
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
        self.assertIn("E102", _codes(result.errors))

    def test_short_description_warns(self) -> None:
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
        self.assertTrue(result.ok)
        self.assertIn("W111", _codes(result.warnings))

    def test_long_description_errors(self) -> None:
        long_desc = "x" * 1100
        source = (
            "---\n"
            "name: long-desc\n"
            f"description: {long_desc}\n"
            "---\n"
            "body\n"
        )
        result = validate_skill_source(source)
        self.assertFalse(result.ok)
        self.assertIn("E112", _codes(result.errors))

    def test_non_string_name_errors(self) -> None:
        source = textwrap.dedent(
            """\
            ---
            name: 123
            description: A description long enough to pass the minimum length check.
            ---
            body
            """
        )
        result = validate_skill_source(source)
        self.assertIn("E101", _codes(result.errors))

    def test_non_string_description_errors(self) -> None:
        source = textwrap.dedent(
            """\
            ---
            name: bad-desc
            description: 42
            ---
            body
            """
        )
        result = validate_skill_source(source)
        self.assertIn("E110", _codes(result.errors))

    def test_secret_leak_detected(self) -> None:
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
        self.assertFalse(result.ok)
        self.assertIn("E200", _codes(result.errors))

    def test_aws_key_detected(self) -> None:
        source = textwrap.dedent(
            """\
            ---
            name: aws-leak
            description: A description long enough to pass the minimum length check.
            ---

            key = AKIAIOSFODNN7EXAMPLE
            """
        )
        result = validate_skill_source(source)
        self.assertIn("E200", _codes(result.errors))

    def test_unknown_field_warns(self) -> None:
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
        self.assertTrue(result.ok)
        self.assertIn("W900", _codes(result.warnings))

    def test_known_optional_fields_no_warning(self) -> None:
        source = textwrap.dedent(
            """\
            ---
            name: full-skill
            description: A description long enough to pass the minimum length check.
            model: sonnet
            argument-hint: <path>
            allowed-tools: Read
            ---
            body
            """
        )
        result = validate_skill_source(source)
        self.assertTrue(result.ok)
        self.assertNotIn("W900", _codes(result.warnings))

    def test_empty_body_warns(self) -> None:
        source = textwrap.dedent(
            """\
            ---
            name: empty-body
            description: A description long enough to pass the minimum length check.
            ---
            """
        )
        result = validate_skill_source(source)
        self.assertIn("W300", _codes(result.warnings))

    def test_frontmatter_must_be_mapping(self) -> None:
        source = "---\n- 1\n- 2\n---\nbody"
        result = validate_skill_source(source)
        self.assertIn("E005", _codes(result.errors))

    def test_empty_frontmatter(self) -> None:
        source = "---\n\n---\nbody"
        result = validate_skill_source(source)
        self.assertIn("E004", _codes(result.errors))

    def test_broken_yaml(self) -> None:
        source = "---\nname: [unclosed\n---\nbody"
        result = validate_skill_source(source)
        self.assertIn("E003", _codes(result.errors))

    def test_allowed_tools_string_ok(self) -> None:
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
        self.assertTrue(result.ok)

    def test_allowed_tools_wrong_type_errors(self) -> None:
        source = textwrap.dedent(
            """\
            ---
            name: tools-int
            description: A description long enough to pass the minimum length check.
            allowed-tools: 42
            ---
            body
            """
        )
        result = validate_skill_source(source)
        self.assertIn("E120", _codes(result.errors))

    def test_allowed_tools_list_items_must_be_strings(self) -> None:
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
        self.assertIn("E121", _codes(result.errors))

    def test_severity_counts_on_result(self) -> None:
        source = "---\nfoo: bar\n---\n"
        result = validate_skill_source(source)
        self.assertTrue(
            all(i.severity is Severity.ERROR for i in result.errors)
        )
        self.assertTrue(
            all(i.severity is Severity.WARNING for i in result.warnings)
        )


class NameRegexTests(unittest.TestCase):
    """Regression coverage for the documented '1-64 chars' name contract."""

    def test_single_character_name_is_valid(self) -> None:
        # Regression: a single-letter name must be accepted (docs say 1-64).
        self.assertIsNotNone(NAME_RE.match("a"))
        source = textwrap.dedent(
            """\
            ---
            name: a
            description: A description long enough to pass the minimum length check.
            ---
            body
            """
        )
        result = validate_skill_source(source)
        self.assertTrue(result.ok)
        self.assertNotIn("E102", _codes(result.errors))

    def test_max_length_name_is_valid(self) -> None:
        self.assertIsNotNone(NAME_RE.match("a" * 64))

    def test_over_max_length_name_is_invalid(self) -> None:
        self.assertIsNone(NAME_RE.match("a" * 65))

    def test_leading_hyphen_rejected(self) -> None:
        self.assertIsNone(NAME_RE.match("-skill"))

    def test_trailing_hyphen_rejected(self) -> None:
        self.assertIsNone(NAME_RE.match("skill-"))

    def test_leading_digit_rejected(self) -> None:
        self.assertIsNone(NAME_RE.match("1skill"))

    def test_internal_hyphens_allowed(self) -> None:
        self.assertIsNotNone(NAME_RE.match("a-b-c"))


class ValidateFileTests(unittest.TestCase):
    def test_validate_skill_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            missing = Path(d) / "nope.md"
            result = validate_skill_file(missing)
            self.assertIn("E000", _codes(result.errors))

    def test_validate_skill_file_directory_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            result = validate_skill_file(d)
            self.assertIn("E000", _codes(result.errors))

    def test_validate_skill_file_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            skill = Path(d) / "SKILL.md"
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
            self.assertTrue(result.ok)
            self.assertEqual(result.path, str(skill))


if __name__ == "__main__":
    unittest.main()
