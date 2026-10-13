# AGENTS.md

Boundaries: none yet.
The package reads no store and calls no service.
Name each one here as you add it, with who writes the data it reads.

## Commands

Setup: `uv sync && uv run pre-commit install`
Check: `./check`
Full check: `./check --full`
One test: `uv run pytest tests/unit/test_logger.py::TestSetupLogging::test_installs_json_formatter_by_default`
Run Python and tools through `uv run`, and add a dependency with `uv add`; never `pip install`, which bypasses `uv.lock`.
Mutation testing by hand: `uv run mutmut run`, then `uv run mutmut results`.

## Constraints

* **Never silence a check to pass it:** a `noqa`, a `type: ignore`, a skip, or a lower `fail_under` hides the next real fault too.
  Fix the cause, or ask the user.
  When the user agrees to silence a ruff rule over a block, use `# ruff: disable[CODE]` and `# ruff: enable[CODE]` rather than a `# noqa` on each line.

## Traps

* uv must be 0.9.17 or later, because `exclude-newer = "7 days"` in `pyproject.toml` is a relative span.
  That setting also makes `uv add` resolve a release from the last 7 days to the one before it.
* Tests run in random order (pytest-randomly).
  Rerun a failure in the same order with `uv run pytest --randomly-seed=last`.
* `mutants/` is mutmut's copy of the tree: edit `src/`, never `mutants/`.

## Pointers

* `[tool.importlinter]` in `pyproject.toml` records what each module owns and which way imports may run.
  Read it before adding a module.
