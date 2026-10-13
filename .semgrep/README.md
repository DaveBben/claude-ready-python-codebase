# Custom rules

This folder holds the project's own Semgrep rules, one per file, for what ruff and mypy cannot express.

When you tell the agent the same thing twice and a static check can express it, write the rule here.
A rule runs on every check, while a line in `AGENTS.md` is advice the model may skip.
Put a correction no check can express in `.claude/rules/` when it applies to some paths, or in `AGENTS.md` when it applies everywhere.

Run them with this command:

```bash
uv run semgrep --config .semgrep --error --quiet
```

## Writing one

* **The message is the prompt:** the agent reads it next, so it says what is forbidden and what to do instead.
  A bare `rule R2011 violated` tells the agent nothing.
* **Scope with `paths:`:** keep exemptions out of the pattern.
* **Find a violation first:** run the rule over the codebase and name the violation it catches.
  A rule with no current violation is a preference, and that is fine when you know it.
* **Watch it fire:** write the violation into a scratch file under `src/`, run the rule, confirm it trips, then delete the file.

## Rules in this folder

| Rule | Forbids |
|---|---|
| `raise-project-error` | Raising a builtin exception from `src/` |
| `no-logging-reconfiguration` | `basicConfig` or `addHandler` outside `logger.py` |
| `logger-name-from-dunder-name` | `logging.getLogger("literal")` |

The codebase had no violation of any of the 3 when they were added.
They keep it that way.
