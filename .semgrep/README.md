# Custom rules

Project-specific rules that ruff and mypy cannot express. One rule per file.

This is where a correction lands. When you find yourself telling the agent the
same thing twice and a static check can express it, write the rule here rather
than adding another line to `CLAUDE.md`: a rule executes, a line of prose is
advice the model may skip. Corrections a check *cannot* express go in
`.claude/rules/` (path-scoped) or `CLAUDE.md` (always loaded) instead.

Run them:

```bash
uv run semgrep --config .semgrep --error --quiet
```

## Writing one

- The `message` is the point. It becomes the prompt the agent reads next, so it
  says what is forbidden *and* what to do instead. `rule R2011 violated` has
  thrown away most of its value.
- Scope with `paths:` rather than writing exemptions into the pattern.
- Before adding a rule, run it against the codebase and find the violation it
  catches. A rule with no current violation is a preference, not a fix — still
  worth having if you want it, but know which one you are adding.
- Verify a new rule actually fires. Write the violation into a scratch file
  under `src/`, run the rule, confirm it trips, then delete the file.

## What is here

| Rule | Forbids | Source |
|---|---|---|
| `raise-project-error` | Raising a builtin exception from `src/` | `src/example_project/CLAUDE.md` |
| `no-logging-reconfiguration` | `basicConfig`/`addHandler` outside `logger.py` | `src/example_project/CLAUDE.md` |
| `logger-name-from-dunder-name` | `logging.getLogger("literal")` | `src/example_project/CLAUDE.md` |

All three were preferences when added: the codebase had zero violations of any
of them. They are here to keep it that way.
