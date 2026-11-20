---
name: python-template
description: "Use first, before creating any file, whenever a new Python project is to be started that will be kept, not thrown away: an app, a CLI, a service or a library, such as 'start a new Python project for X', 'scaffold a Python CLI', 'set up a repo for my Python tool', 'create a package called acme_tools' or 'new uv project for the scraper'. Not for a one-off script, a spike or a notebook. Copies a uv src-layout template with its checks, Claude Code hooks, pre-commit and CI, renames it to the project and fills in the project's own text with the person."
license: MIT
compatibility: Requires uv 0.9.17 or later and git 2.28 or later.
metadata:
  version: "3.0.0"
---
# Python template

`assets/project/` is a src-layout package named `example_project` with every gate already wired: ruff, mypy, import-linter, semgrep rules, vulture, deptry, zizmor, pytest with a coverage floor, pip-audit, gitleaks and mutmut, all behind `./check`, plus Claude Code hooks that run it at turn end and before a pull request, pre-commit, and a CI workflow. Never scaffold a project by hand when this applies.

## Ask once

Ask in one message, with your suggestion for each, inferred from what the person already said:

* **Import name:** a lowercase identifier such as `acme_tools`. The distribution name `acme-tools` and the base exception `AcmeToolsError` follow from it.
* **Directory:** where the project goes; it must not exist yet or be empty.
* **What it does,** in one sentence.
* **Copyright holder** for the MIT `LICENSE`, and whether MIT is the license they want. The year is this year.
* **Container and editor files:** keep or drop the `Dockerfile`, `docker-compose.yml` and `.dockerignore`, the `.devcontainer/`, and `.vscode/`.

## Create it

```bash
uv run <this skill>/scripts/new_project.py <directory> <import_name> "<what it does>" "<copyright holder>"
```

It builds the project in a temporary directory and moves it into place only once it is complete: it renames the package, the test file and all 3 spellings of the name, writes the sentence into `pyproject.toml`, the package docstring and `README.md`, and the holder and year into `LICENSE`, and runs `git init -b main`. It refuses a name that would break the project, such as one that shadows a standard-library module, and a directory that is not empty, and fails when any old name is left. Run it with `uv run`, which supplies the Python 3.12 it needs. Then, in the new directory:

```bash
uv lock && uv sync
uv run ruff check --fix . && uv run ruff format .
uv run pre-commit install
```

## Make it theirs

* **Another license:** replace `LICENSE` and change `license` in `pyproject.toml`.
* **`AGENTS.md`:** leave `Boundaries: none yet.` until the project reads a store or calls a service; then name each one with who writes the data it reads. `CLAUDE.md` is a symlink to it, and `./check` fails if it becomes a copy.
* **Dropped Docker files:** also remove the `docker` entry from `.github/dependabot.yml`.
* **A library with no CLI:** the entry point is `[project.scripts]`, `src/<name>/__main__.py`, its test in `tests/unit/test_<name>.py`, its ruff per-file ignore, the first import-linter layer, which must then start at `logger`, and the "Run it" section of `README.md`. Kept container and editor files also name it: the `Dockerfile` `ENTRYPOINT`, the comment atop `docker-compose.yml`, and the module in `.vscode/launch.json`. Keep the CLI unless the person asks otherwise.
* **The Python floor** is set in 3 places that move together: `requires-python`, ruff's `target-version` and the lowest entry of the CI test matrix. The dev version, in `.python-version`, both `FROM` lines of the `Dockerfile` and the `.devcontainer/devcontainer.json` image, must stay at or above it.

## Done

Done is `./check` passing in the new directory. Report that with its result, and what you did not run, such as `./check --full`, which needs gitleaks on the `PATH`. Then offer a first commit that names each top-level path, since a blanket `git add .` is blocked, and creating a GitHub repository, which the person must confirm because it publishes the code.
