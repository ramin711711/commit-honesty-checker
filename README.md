# commit-honesty-checker

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude API](https://img.shields.io/badge/AI-Claude-purple.svg)](https://www.anthropic.com/)

A CLI tool and git hook that checks whether a commit message actually describes what changed — flagging things like a "fix typo" commit that quietly rewrites half a file.

Two independent detection layers: a rule-based size check and an AI-powered semantic check, each catching a different category of misleading commit message.

## Example

```
$ python commit_checker.py -o HEAD~1 -n HEAD -t 20

Did NOT pass the initial observation❌

Commit message accuracy: 2/10
Reasoning: The commit message 'final small fix test' is vague and inaccurate. The diff
shows an entirely new 38-line file implementing a number analysis function — not a
small fix, but a new feature.
Suggested message: Add number analysis function with statistical calculations
```

## How it works

```
commit message + diff
        │
        ├── rule-based layer   → parses the diff, counts touched lines, checks
        │                         the message for size claims ("typo", "minor",
        │                         "quick fix") using regex word-boundary matching
        │
        └── AI layer (Claude)  → reads message + diff together, returns a
                                    1-10 accuracy score, reasoning, and a
                                    suggested rewrite
```

Both layers run and report independently — they're not redundant. The rule-based layer catches *size* mismatches ("small fix" on a 200-line diff) instantly and for free. The AI layer catches *semantic* mismatches a line-count can never see — a message describing something the diff doesn't actually do, regardless of size.

If the AI call fails or returns malformed output, the tool falls back to the rule-based result alone rather than crashing.

## Install

```bash
git clone https://github.com/ramin711711/commit-honesty-checker.git
cd commit-honesty-checker
pip install -r requirements.txt
cp .env.example .env   # then add your ANTHROPIC_API_KEY
```

## Usage

**Standalone:**
```bash
python commit_checker.py -o <old_commit> -n <new_commit> -t <threshold> [--strict]
```

| Flag | Meaning |
|---|---|
| `-o`, `--old_commit` | commit to diff from (e.g. `HEAD~1`) |
| `-n`, `--new_commit` | commit to diff to — also the commit whose message is checked |
| `-t`, `--threshold` | line-count cutoff for "too big to be a small fix" (default 20) |
| `--strict` | exit non-zero if the AI score is below 5, for use in scripts/CI |

**As a git hook (runs automatically on every commit):**
```bash
cp commit_msg_hook.py /path/to/repo/.git/hooks/commit-msg
chmod +x /path/to/repo/.git/hooks/commit-msg
```
The hook blocks by default rather than just warning — installing it is an explicit opt-in to enforcement, unlike the CLI which stays informational unless `--strict` is passed.

## Notable design decisions

- **`subprocess` over `gitpython`** — parsing raw diff text directly (hunk headers, `+`/`-` lines) instead of going through a library that abstracts it away.
- **Regex word-boundary matching, not substring matching** — an earlier version flagged "Reformat docstrings" because "format" appeared as a substring, even though the message wasn't claiming smallness. Fixed with `\bkeyword\b` matching.
- **AI output isn't trusted blindly** — responses are stripped of markdown fences and parsed defensively inside a try/except, since prompting for clean JSON reduces but doesn't guarantee malformed output.
- **CLI warns by default, hook blocks by default** — different entry points imply different intent. Running the CLI manually is exploratory; installing a hook is a deliberate choice to enforce.

## Known limitations

- The hook currently resolves `commit_checker.py` via a path added to `sys.path` at runtime — this needs updating if the repo is cloned somewhere other than its original location.
- The size threshold is a fixed number rather than scaled to repo size.
- Keyword matching is word-level, not intent-level — a message like "minor formatting pass across 40 files" can still get flagged even when "minor" is an accurate description.

## Roadmap

- [ ] GitHub Action version, so the check runs on PRs without every contributor installing the hook locally
- [ ] Threshold scaled to repo/file size
- [ ] Cache AI evaluations by diff hash to avoid redundant API calls

## Stack

Python · Claude API (Anthropic) · `subprocess` · `argparse` · `python-dotenv`

## License

MIT — see [LICENSE](LICENSE).
