# example-project

A Python project template built **Claude-first**: TDD by default, with current Python best practices baked in.

## The core idea

A coding agent works best with two things: fast feedback on whether its code is right, and a context window that isn't buried in noise. This repo gives it both.

## Quick start

Fork this repo on GitHub, then:

```bash
git clone https://github.com/<you>/<your-fork>.git my-project
cd my-project
uv sync                    # build the venv with every dev tool
uv run pre-commit install  # enable the commit-time quality gate (one time)
```

That's the whole setup. Confirm it works:

```bash
uv run example-project     # run the example CLI
```

Then make it yours: rename `src/example_project/` and the matching names in `pyproject.toml`, and add dependencies with `uv add`.

## Running the checks

```bash
uv run pytest                # full test suite
uv run pytest --cov          # …with branch coverage and missing lines
uv run mypy src tests        # strict type check
uv run ruff check src tests  # lint
uv run ruff format src tests # format
uv run semgrep --config .semgrep --error --quiet   # this repo's own rules
uv run lint-imports          # architectural contracts
```

You rarely need these by hand. Claude Code hooks lint every edit, then check types, architecture, and the custom rules at the end of every turn; pre-commit runs all of that plus dead code and the test suite on every commit, and a dependency CVE audit whenever `uv.lock` changes. The full gate as one line, for CI or an on-demand check:

```bash
uv run ruff check src tests && uv run ruff format --check src tests \
  && uv run semgrep --config .semgrep --error --quiet \
  && uv run mypy src tests && uv run lint-imports \
  && uv run vulture && uv run pip-audit && uv run pytest --cov
```

## The dev container

`.devcontainer/` gives you an isolated Linux environment for both you and any AI agent. The container can't reach your home directory, SSH keys, or host files, so an agent's blast radius is one disposable container. Open the repo in VS Code with the Dev Containers extension and run **Reopen in Container**, or launch it headless with the `devcontainer` CLI. On create it builds the venv (off the mounted repo, so it never clashes with a host `.venv`), installs the commit gate, and installs the Claude Code CLI.

### Running Claude Code in the container

In the container terminal:

```bash
claude    # first run logs you in via the browser; the token persists in a volume
```

Because the container is sandboxed, you can drop the permission prompts and let the agent iterate freely:

```bash
claude --dangerously-skip-permissions
```

**Authentication, safest first:**

- **Browser login (default, no secret).** The token lives in the `~/.claude` volume — nothing to inject, nothing to commit. Use this unless you have a reason not to.
- **API key, if you need headless/non-interactive auth.** Don't pass it as an env var: `containerEnv` values are visible in `docker inspect`, at `/proc/<pid>/environ`, and to every child process — so in a `--dangerously-skip-permissions` sandbox the agent itself can read and exfiltrate the key. Instead mount the key as a **read-only file** and have Claude read it on demand:

  ```jsonc
  // .devcontainer/devcontainer.json — mount a host key file, never a literal
  "mounts": [
    "source=${localEnv:HOME}/.config/anthropic/key,target=/home/vscode/.config/anthropic/key,type=bind,readonly=true"
  ]
  ```
  ```jsonc
  // .claude/settings.json (or ~/.claude/settings.json) — read it on demand, not from env
  { "apiKeyHelper": "cat /home/vscode/.config/anthropic/key" }
  ```
  A `0400` file isn't in `docker inspect`, isn't in the process environment, and isn't inherited by child processes. (An API key bills per-token, separate from a Pro/Max plan.)

## What's included

- **A three-layer verification loop** — ruff fixes every edit; types, architecture, and the custom rules run at the end of every turn; pre-commit runs the whole gate (tests included) on every commit.
- **Rules of your own** — `.semgrep/` holds the checks ruff can't express, one per file, each with a failure message written as a prompt. This is where a correction lands, so you never make it twice.
- **Architectural tests** — `[tool.importlinter]` states which way dependencies are allowed to run and enforces it. The only check in the gate that can tell you a boundary moved.
- **Strict tooling with no escape hatches** — an agent-focused ruff rule set, mypy `--strict`, pytest with warnings as errors, Hypothesis profiles (fast locally, thorough in CI), vulture for dead code, pip-audit for CVEs, and a gitleaks secret scan.
- **A TDD workflow** — behavior changes go one failing test at a time, red confirmed before green.
- **Agent instructions that respect the context window** — a short `CLAUDE.md`, plus path-scoped rules and nested files that load only when relevant. `AGENTS.md` symlinks to it, so Codex, Cursor, Copilot, and other tools read the same guidance.
- **A clean package skeleton** — src layout, a typed exception root, `py.typed`, and zero runtime dependencies.
- **Structured logging by default** — a stdlib JSON logger (no dependency) wired into the CLI; set `LOG_LEVEL` or `LOG_JSON=false` to tune it.
- **Editor parity** — `.vscode/` and `.editorconfig` mirror the commit gate, so the editor and the hooks never disagree.
- **A container build** — a multi-stage `Dockerfile` (uv build to a minimal non-root runtime) and a `docker-compose.yml` for one-shot runs: `docker compose run --rm app`.
- **A dev container** — `.devcontainer/` runs the agent in an isolated environment (no host home dir or SSH keys), with the venv and commit gate set up on create.
- **CI that runs the same gate** — a GitHub Actions workflow runs lint, format, the custom rules, types, architecture, dead code, the CVE audit, and tests on every PR, across Python 3.12, 3.13, and 3.14.
- **Automated dependency updates** — a `renovate.json` keeps `pyproject.toml`, `uv.lock`, and CI action pins current.
