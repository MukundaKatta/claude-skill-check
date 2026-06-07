# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- `name` validation now accepts a single-character name (e.g. `a`), matching the
  documented "1-64 characters" contract. The previous regex required at least
  two characters and wrongly reported `E102` for valid one-character names.

### Added
- `validate_paths` is now exported from the top-level `claude_skill_check`
  package and documented in the README API table.
- `py.typed` marker (PEP 561) and the `Typing :: Typed` classifier so type
  checkers consume the package's annotations.
- Standard-library `unittest` test suite (no third-party runner required),
  runnable with `python -m unittest discover -s tests`, including CLI exit-code /
  quiet-mode / recursive-scan tests and name-regex regression coverage.

### Changed
- CI now runs the suite under both `unittest` and `pytest`.

## [0.1.0] - 2026-04-23

### Added
- Initial release.
- `claude-skill-check` CLI that lints one or more `SKILL.md` files (or directories scanned recursively).
- Library surface: `validate_skill_file`, `validate_skill_source`, `ValidationResult`, `Issue`, `Severity`.
- Checks: YAML frontmatter present and parseable, `name` / `description` required, `name` is lowercase kebab-case, `description` length 20-1024 chars, `allowed-tools` shape, unknown fields flagged as warnings, empty body flagged as warning.
- Secret-leak detection for Anthropic / OpenAI / AWS keys, GitHub tokens, and PEM private-key blocks.
- 16 tests covering the validator.
- GitHub Actions: CI on Python 3.9 - 3.13, and a release workflow that publishes to PyPI via OIDC trusted publishing.
