# example-project

<!-- What it does and who it is for, in 1 to 3 sentences. -->

## Set up once

You need uv 0.9.17 or later, because `pyproject.toml` sets `exclude-newer = "7 days"`, a relative span that older uv rejects.
Check with `uv --version`, and update with `uv self update` or your package manager.

```bash
uv sync
uv run pre-commit install
```

`./check --full` also needs [gitleaks](https://github.com/gitleaks/gitleaks) on the `PATH`, such as from `brew install gitleaks`.

## Run it

```bash
uv run example-project
```

## Run the checks

```bash
./check         # format, lint, types, import contracts, semgrep, dead code, deptry, zizmor, tests with the coverage floor
./check --full  # ./check, then pip-audit (reported, not gated), gitleaks over the branch, and mutmut over the modules changed since main
./check --scheduled  # mutmut over all of src/, for CI's schedule; gates nothing
```

They also run on their own:

* **Claude Code turn end:** `.claude/hooks/gate.py` runs `./check` when the tree changed.
* **Before a pull request opens:** `.claude/hooks/gate.py` runs `./check --full`.
* **On commit and push:** pre-commit runs the fast checks, typos, and gitleaks on commit, and mypy, semgrep, and the tests on push.
* **In CI:** `.github/workflows/ci.yml` runs the lint and test jobs on each pull request and each push to main.
