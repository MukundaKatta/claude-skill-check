"""Tests for the claude-skill-check command-line interface.

Standard-library ``unittest`` only; runnable with either
``python -m unittest discover -s tests`` or ``pytest``.
"""

from __future__ import annotations

import io
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from claude_skill_check.cli import main

VALID = textwrap.dedent(
    """\
    ---
    name: good-skill
    description: A description long enough to pass the minimum length check.
    ---

    # Body
    """
)

INVALID = textwrap.dedent(
    """\
    ---
    name: BadName
    description: A description long enough to pass the minimum length check.
    ---

    # Body
    """
)


class CliExitCodeTests(unittest.TestCase):
    def _write(self, directory: Path, name: str, content: str) -> Path:
        p = directory / name
        p.write_text(content)
        return p

    def test_valid_file_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = self._write(Path(d), "SKILL.md", VALID)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main([str(path)])
            self.assertEqual(code, 0)
            self.assertIn("OK", out.getvalue())

    def test_invalid_file_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = self._write(Path(d), "SKILL.md", INVALID)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main([str(path)])
            self.assertEqual(code, 1)
            self.assertIn("E102", out.getvalue())

    def test_no_files_found_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            # Empty directory: no SKILL.md anywhere.
            err = io.StringIO()
            with redirect_stderr(err):
                code = main([d])
            self.assertEqual(code, 2)
            self.assertIn("no SKILL.md files found", err.getvalue())

    def test_directory_is_scanned_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            nested = Path(d) / "a" / "b"
            nested.mkdir(parents=True)
            self._write(nested, "SKILL.md", VALID)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main([d])
            self.assertEqual(code, 0)
            self.assertIn("SKILL.md", out.getvalue())

    def test_quiet_hides_ok_lines(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self._write(Path(d), "SKILL.md", VALID)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--quiet", d])
            self.assertEqual(code, 0)
            self.assertNotIn("OK", out.getvalue())

    def test_quiet_still_shows_errors(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self._write(Path(d), "SKILL.md", INVALID)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--quiet", d])
            self.assertEqual(code, 1)
            self.assertIn("E102", out.getvalue())

    def test_mixed_results_exit_one(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            good = Path(d) / "good"
            bad = Path(d) / "bad"
            good.mkdir()
            bad.mkdir()
            self._write(good, "SKILL.md", VALID)
            self._write(bad, "SKILL.md", INVALID)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main([d])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
