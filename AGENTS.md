# AGENTS.md

Boundaries: none yet.
The package reads no store and calls no service.
Name each one here as you add it, with who writes the data it reads.

## Commands

Setup: `uv sync && uv run pre-commit install`
Check: `./check`
Full check: `./check --full`
Scheduled check: `./check --scheduled`
One test: `uv run pytest tests/unit/test_logger.py::TestSetupLogging::test_installs_json_formatter_by_default`
Run Python and tools through `uv run`, and add a dependency with `uv add`; never `pip install`, which bypasses `uv.lock`.
Mutation testing by hand: `./check --scheduled`, then `uv run mutmut results`.

## Constraints

* **Never lower `fail_under` to pass coverage:** it hides the next real fault too.
  Add the test, or ask the user.

## Traps

* uv must be 0.9.17 or later, because `exclude-newer = "7 days"` in `pyproject.toml` is a relative span.
  That setting also makes `uv add` resolve a release from the last 7 days to the one before it.
* Tests run in random order (pytest-randomly).
  Rerun a failure in the same order with `uv run pytest --randomly-seed=last`.
* `mutants/` is mutmut's copy of the tree: edit `src/`, never `mutants/`.
* On macOS, a mutant mutmut reports as "segfault" is usually the system proxy lookup crashing after fork(), not the test.
  httpx, requests and urllib make that lookup; set `no_proxy` in the tests (an autouse `monkeypatch.setenv("no_proxy", "*")`) and it is skipped.

## Pointers

* `[tool.importlinter]` in `pyproject.toml` records what each module owns and which way imports may run.
  Read it before adding a module.
