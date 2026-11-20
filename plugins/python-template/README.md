# python-template

1 skill. It starts a Python project you mean to keep from a template with every check already wired.

## What runs in a session

- **The `python-template` skill:** loads when you ask for a new Python project that is not throwaway, such as "start a new Python CLI called acme_tools". It asks, in one message, for the import name, the directory, a one-sentence description, the copyright holder, and which container and editor files to keep. Then `scripts/new_project.py` builds the project in a temporary directory: it renames the package and every spelling of its name, writes in your description and license holder, runs `git init`, and moves the project into place only once it is complete. The agent then locks and syncs it with uv, installs pre-commit, and is done when the new project's `./check` passes.
- **No hooks of its own:** the hooks ship inside each new project, in its `.claude/settings.json`.

A one-off script, a spike or a notebook skips the skill.
