# claude-skill-check

A small Python linter for [Claude Code](https://claude.ai/code) `SKILL.md` files. It checks:

- YAML frontmatter is present and parses cleanly
- `name` and `description` are present
- `name` is lowercase kebab-case, 1-64 chars, starts with a letter
- `description` length is reasonable (20-1024 chars after trimming)
- `allowed-tools` is either a string or a list of strings
- Common secret patterns (Anthropic/OpenAI keys, AWS access keys, GitHub tokens, PEM blocks) are not leaked in the file
- Unknown frontmatter fields get a warning
- Empty body gets a warning

## Install

```bash
pip install claude-skill-check
```

## Usage

Lint a single file:

```bash
claude-skill-check path/to/SKILL.md
```

Lint every `SKILL.md` under a directory:

```bash
claude-skill-check path/to/skills-dir/
```

Exit status: `0` on no errors, `1` on any errors, `2` when no skill files were found.

### Only show errors

```bash
claude-skill-check --quiet path/to/skills-dir/
```

## Use as a library

```python
from claude_skill_check import validate_skill_file

result = validate_skill_file("path/to/SKILL.md")
if not result.ok:
    for issue in result.errors:
        print(issue.code, issue.message)
```

## Issue codes

| Code  | Severity | Meaning                                                           |
|-------|----------|-------------------------------------------------------------------|
| E000  | error    | file not found or not a regular file                              |
| E001  | error    | file is empty or not valid UTF-8                                  |
| E002  | error    | missing YAML frontmatter                                          |
| E003  | error    | frontmatter is not valid YAML                                     |
| E004  | error    | frontmatter is empty                                              |
| E005  | error    | frontmatter is not a mapping                                      |
| E100  | error    | missing required field (`name` or `description`)                  |
| E101  | error    | `name` is not a string                                            |
| E102  | error    | `name` is not a valid kebab-case identifier                       |
| E110  | error    | `description` is not a string                                     |
| E112  | error    | `description` exceeds 1024 chars                                  |
| E120  | error    | `allowed-tools` is not a string or list                           |
| E121  | error    | `allowed-tools` list contains a non-string item                   |
| E200  | error    | possible secret detected in the skill file                        |
| W111  | warning  | `description` is shorter than 20 chars                            |
| W300  | warning  | skill body is empty after frontmatter                             |
| W900  | warning  | unknown frontmatter field                                         |

## Development

```bash
pip install -e '.[dev]'
pytest
```

## License

MIT
