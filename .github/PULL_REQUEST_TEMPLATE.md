## What changed

<!-- Brief description of what this PR does -->

## Why

<!-- What problem does this solve, or what feature does it add? -->

## Testing

<!-- How did you verify this works? -->

## Checklist

- [ ] Gate passes: `uv run ruff check src tests && uv run ruff format --check src tests && uv run semgrep --config .semgrep --error --quiet && uv run mypy src tests && uv run lint-imports && uv run vulture && uv run pip-audit && uv run pytest --cov`
- [ ] Behavior changes ship with tests (bug fixes add a failing regression test first)
- [ ] Docs updated where this change makes them wrong (CLAUDE.md, README, nested CLAUDE.md)
- [ ] A new boundary or dependency direction has a contract in `[tool.importlinter]`
- [ ] Nothing was silenced to get green (no new `noqa`, `# type: ignore`, `skip`/`xfail`, or loosened config without a stated reason)
- [ ] No credentials, keys, or secrets included
