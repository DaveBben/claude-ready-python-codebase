# python-template

A skill for creating python projects utilizing the latest best practices.

## What you get

A new project with:

- **One check command:** `./check` runs ruff, mypy, import-linter, semgrep rules, vulture, deptry, zizmor and the tests with a coverage floor. `./check --full` adds pip-audit, gitleaks and mutmut over the modules changed since main.
- **Claude Code hooks:** `./check` runs at turn end and `./check --full` before a pull request opens. `pip install`, blanket `git add`, skipped git hooks, and unknown or brand-new PyPI packages are blocked.
- **pre-commit and CI:** fast checks, typos and gitleaks on commit, the slow ones on push, and a GitHub Actions workflow with a Python version matrix.
- **An `AGENTS.md`** with the commands, constraints and traps an agent needs, and `CLAUDE.md` as its symlink.

## Install

```bash
claude plugin marketplace add DaveBben/python-template-skill
claude plugin install python-template@python-template
```

Then start a new session, or run `/reload-plugins` in one that's open. Other agents: `npx skills add DaveBben/python-template-skill --all`.

## How to use it

Ask for the project, such as "start a new Python CLI called acme_tools". The agent asks, all in one message, for the import name, the directory, a one-sentence description, and which container and editor files to keep. Then it creates the project and runs `./check` there.

You need uv 0.9.17 or later and git 2.28 or later, and gitleaks for a project's `./check --full`.

MIT license.
