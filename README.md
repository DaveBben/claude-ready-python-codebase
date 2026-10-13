# claude-ready-python-codebase

This repository is a GitHub template for a Python project that an AI coding agent such as Claude Code works in.
It ships a src-layout package named `example_project`, the checks that gate every change, and the Claude Code hooks that run them.

## Start a project

Create a repository from the template with the GitHub CLI, or with **Use this template** on the GitHub page:

```bash
gh repo create my-project --template DaveBben/claude-ready-python-codebase --private --clone
cd my-project
```

## Set up once

You need uv 0.9.17 or later, because `pyproject.toml` sets `exclude-newer = "7 days"`, a relative span that older uv rejects.
Check with `uv --version`, and update with `uv self update` or your package manager.

```bash
uv sync
uv run pre-commit install
```

`./check --full` also needs [gitleaks](https://github.com/gitleaks/gitleaks) on the `PATH`, such as from `brew install gitleaks`.

## Run the checks

These 2 commands cover every gate:

```bash
./check         # format, lint, types, import contracts, semgrep, dead code, deptry, zizmor, tests with the coverage floor
./check --full  # ./check, then pip-audit, gitleaks over the branch, and mutmut over the modules changed since main
./check --scheduled  # mutmut over all of src/, for CI's schedule; gates nothing
```

They also run on their own:

* **Claude Code turn end:** `.claude/hooks/gate.py` runs `./check` when the tree changed.
* **Before a pull request opens:** `.claude/hooks/gate.py` runs `./check --full`.
* **On commit and push:** pre-commit runs the fast checks, typos, and gitleaks on commit, and mypy, semgrep, and the tests on push.
* **In CI:** `.github/workflows/ci.yml` runs the lint and test jobs on each pull request and each push to main.

## Rename the template

Replace the package name everywhere, then confirm nothing is left.
In these steps, `my_project` is the import name, `my-project` the distribution name, and `MyProject` the prefix of the base exception `MyProjectError`.

1. Move the package and its test file:

   ```bash
   git mv src/example_project src/my_project
   git mv tests/unit/test_example_project.py tests/unit/test_my_project.py
   ```

2. Replace the 3 spellings of the name in every tracked file:

   ```bash
   git grep -lz -e example_project -e example-project -e ExampleProject |
     xargs -0 perl -pi -e 's/example_project/my_project/g; s/example-project/my-project/g; s/ExampleProject/MyProject/g'
   ```

   This reaches each file below:

   * **`pyproject.toml`:** `name`, the `[project.scripts]` entry, the hatch package and version paths, the ruff per-file ignore and `known-first-party`, and the import-linter `root_package` and contract modules.
   * **`src/` and `tests/`:** the imports, `ExampleProjectError`, the CLI banner, and the logger names in the tests.
   * **`.semgrep/`:** the paths and the exception name in `raise-project-error.yml` and `no-logging-reconfiguration.yml`.
   * **Container and editor files:** the `Dockerfile` entry point, the `docker-compose.yml` image, the `.devcontainer/devcontainer.json` name, and the `.vscode/launch.json` module.
   * **`uv.lock`:** the project's own entry.

3. Sort the imports the rename reordered, and refresh the lock:

   ```bash
   uv run ruff check --fix . && uv run ruff format .
   uv lock
   ```

4. Write the project's own text by hand:

   * **`pyproject.toml`:** `description`.
   * **`src/my_project/__init__.py`:** the module docstring.
   * **`README.md`:** replace this file with the project's README.
   * **`LICENSE`:** the copyright holder and year, when they differ.
   * **`AGENTS.md`:** the `Boundaries:` line, once the project reads a store or calls a service.

5. Confirm that no old name is left and that the checks pass:

   ```bash
   git grep -n -i -e 'example.project' -e ExampleProject
   ./check
   ```

   The `git grep` prints nothing when the rename is complete.
