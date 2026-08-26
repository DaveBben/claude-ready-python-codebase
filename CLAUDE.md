# CLAUDE.md

Guidance for AI coding agents working in this repository.

## Contents

1. [Project Identity](#project-identity)
2. [Tech Stack and Codebase Map](#tech-stack-and-codebase-map)
3. [Operational Commands](#operational-commands)
4. [Workflow](#workflow)
5. [Critical Constraints](#critical-constraints)
6. [Pointers to Deeper Docs](#pointers-to-deeper-docs)

## Project Identity

A template Python codebase

## Tech Stack and Codebase Map

- **Language**: Python. Dev on 3.13 (`.python-version`). Support floor is 3.12.
- **Package manager**: uv (`uv.lock` is authoritative).
- **Runtime dependencies**: none. This is a scaffold; add yours with `uv add`.
- **Tooling**: ruff (lint + format), semgrep (this repo's own rules), mypy (strict types), import-linter (architectural contracts), pytest (tests), vulture (dead code), pip-audit (dependency CVEs), pre-commit (commit-time gate).
- **Container**: multi-stage `Dockerfile` (uv build → minimal non-root runtime) and a `docker-compose.yml` for one-shot runs.

### Directory Layout

- `src/example_project/` — example package
- `tests/` — pytest suite
- `.semgrep/` — this repo's own rules, one per file
- `.claude/` — Claude Code settings, hooks, and path-scoped rules
- `.devcontainer/` — isolated dev/agent environment (uv + commit gate on create)
- `.vscode/` — VS Code settings
- `.github/` — CI workflow (runs the full gate on PRs) and the PR template

## Operational Commands

```bash
uv sync                      # install deps (including dev group)
uv run example-project   # run the CLI
uv run pytest                # all tests
uv run pytest path::test     # a single test
uv run pytest --cov          # tests with coverage
uv run mypy src tests        # strict type check
uv run ruff check src tests  # lint
uv run ruff format src tests # format
uv run semgrep --config .semgrep --error --quiet   # this repo's own rules
uv run lint-imports          # architectural contracts
uv run vulture               # dead-code scan
uv run pip-audit             # dependency CVE scan
uv run pre-commit install    # enable git-commit guardrails (one time)
```

The full gate, as one line (pre-commit enforces all of it at commit except the coverage report; use this for CI or an on-demand full check):

```bash
uv run ruff check src tests && uv run ruff format --check src tests \
  && uv run semgrep --config .semgrep --error --quiet \
  && uv run mypy src tests && uv run lint-imports \
  && uv run vulture && uv run pip-audit && uv run pytest --cov
```

## Workflow

**Use TDD.** Write the failing test first and confirm it fails, then write the minimal code to pass.

**Every correction becomes a rule.** When the user has to tell you the same
thing twice, the fix is not to remember harder, it is to write the check. Where
it goes:

| The correction is… | Goes in |
|---|---|
| Expressible as a static check | `.semgrep/<rule>.yml` |
| A dependency-direction rule | A contract in `[tool.importlinter]` |
| Not checkable, and file-specific | `.claude/rules/*.md`, with `paths:` frontmatter |
| Not checkable, and true all conversation | This file |

## Critical Constraints

- **Every function must be fully type-annotated.** mypy runs `--strict`; untyped code fails.
- **Behavior changes ship with tests.** New behavior gets a test at its public seam; bug fixes get a failing regression test first.
- **Fail loud.** never swallow an exception silently
- **Green by suppression is not green.** Silencing a check is not the same as passing it.
- **Run the checks; don't just trust the diff.** Never claim a check passed without running it.
- **Keep the docs current.** When a change makes this file, the README, or a nested `CLAUDE.md` wrong, fix it in the same change.

## Pointers to Deeper Docs

- `README.md` — overview and quick start.
- `.semgrep/README.md` — how to write one of this repo's own rules.
- `[tool.importlinter]` in `pyproject.toml` — what each module owns and which
  way dependencies are allowed to run. There is no separate architecture doc;
  the contracts are the record.
