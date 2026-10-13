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
| `no-noqa` | A `# noqa` comment; fix the cause, or `# ruff: disable[CODE]` over a block when the user agrees |
| `no-type-ignore` | A `# type: ignore` comment; fix the type, narrow it, or cast with a reason |
| `no-skipped-tests` | `@pytest.mark.skip` or `pytest.skip()`; `skipif` with a reason stays allowed |

The codebase had no violation of any of the 6 when they were added, once the one `# type: ignore` in the tests was typed properly.
They keep it that way.

## Fixtures

A rule with a fixture has a `.py` file of the same name beside it, annotated with `# ruleid:` and `# ok:`.
`semgrep --test` skips hidden folders, so `semgrep --test --config .semgrep/` finds nothing; name the pair:

```bash
uv run semgrep --test --config .semgrep/no-noqa.yml .semgrep/no-noqa.py
```
