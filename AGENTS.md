# Guide for agents

`python-template` is one plugin with one skill: it starts a kept Python project from the template bundled in the skill.

Setup: `uvx pre-commit install`, for gitleaks and typos on commit.
Definition of done: `./check`

`./check` checks the plugin manifests, lints and self-tests `new_project.py`, makes a project with it in a temporary directory, and runs that project's own `./check`. `./check --full` adds pip-audit there, which reports known vulnerabilities and fails on none of them.

## Key files

- `skills/python-template/python-template/SKILL.md` is the skill. Edit it only there.
- `skills/python-template/python-template/assets/project/` is the template, a working project named `example_project`. Its `AGENTS.md`, `README.md`, `.pre-commit-config.yaml` and `.github/` are for the projects made from it, not for this repository.
- `skills/python-template/python-template/scripts/new_project.py` makes a project from the template. It fails when any old name or the template's description is left, so new template text that must change per project belongs either in the script or in `SKILL.md`'s "Make it theirs".
- `plugins/python-template/` is the Claude Code wrapper: `.claude-plugin/plugin.json`, a README, and `skills`, a symlink into `skills/python-template`. Do not replace the symlink with real files.
- `.claude/hooks` and `.claude/settings.json` are symlinks to the template's. `guard.py` and `gate.py` guard this repository too; `post-edit.sh` does not, because the root has no `pyproject.toml`.
- `ruff.toml` lints the scripts with the template's rules.

## Rules for changes

- **Template work:** run `uv sync` and `./check` inside `assets/project/`, through `uv run`. Never `pip install`.
- **Plugin installs copy symlinks as plain files,** so anything the template needs as a link is recreated by `new_project.py`, as it does for `CLAUDE.md`.
- **Version:** keep the version in `plugin.json`, in `marketplace.json` and in `SKILL.md`'s `metadata` equal, and bump them together. `./check` fails when they differ.
- **Skill paths** in `marketplace.json` are `./skills/<skill>`, relative to the plugin `source`, with no `..`.
- **Skill format:** follow the Agent Skills specification at <https://agentskills.io/specification.md>. Lead the `description` with the trigger.
- **Wording:** write for the agent. Give it the knowledge it lacks, with no rule it would follow unprompted.
