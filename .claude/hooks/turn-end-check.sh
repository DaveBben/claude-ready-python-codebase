#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Stop hook — the whole-package checks, before the agent hands work back.
#
# WHY THIS EXISTS
#   The PostToolUse ruff hook deliberately runs one file at a time. The Stop
#   event fires once, when Claude believes it is finished — the right moment for
#   the checks that need the whole package and are too slow for every edit.
#   Exit 2 blocks the stop and returns the errors, so the agent fixes them
#   before a human ever reviews the work.
#
# WHAT RUNS, IN ASCENDING COST
#   mypy src tests The type oracle, over the package AND the suite. A test the
#                  type checker never reads is a test nothing verifies.
#   lint-imports   The architectural contracts in pyproject.toml. The ONLY check
#                  in the whole gate that can tell you a dependency now runs the
#                  wrong way; ruff and mypy see one file at a time and have no
#                  opinion about the shape of the package.
#   semgrep        This repo's own rules, in .semgrep/. Where corrections land,
#                  so it belongs where the agent still has the change in
#                  context rather than at commit time.
#
#   Roughly 2.5s together on this repo, with a warm mypy cache. If semgrep grows
#   past a few seconds as the codebase does, drop it from here and let the
#   commit gate carry it — a slow check in a fast layer gets disabled inside a
#   week.
#
#   && not ;: the first failure is the one to fix, and three checks' worth of
#   output at once buries it.
#
# WHY NOT THE REST OF THE GATE
#   vulture, pip-audit and pytest --cov belong in pre-commit and CI. A Stop hook
#   fires at the end of EVERY turn, including trivial ones; pip-audit needs the
#   network and pytest can take a while.
#
# LOOP SAFETY
#   Two guards prevent runaway loops and pointless runs:
#   1. A per-session retry counter, keyed by session_id in TMPDIR. Each
#      blocked stop increments it; a green check clears it. After 3 blocks
#      the hook gives up and lets the stop through, so an unfixable error
#      can't trap the agent forever. (This replaces the old stop_hook_active
#      bail, which verified only once — the fix made after the first block
#      was never re-checked.)
#   2. Skip entirely when no .py file is modified (vs HEAD or untracked):
#      a Q&A turn that edited nothing shouldn't pay for the checks.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

root="${CLAUDE_PROJECT_DIR:-.}"

# Guard 1: retry counter (see LOOP SAFETY above).
sid="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("session_id",""))' 2>/dev/null || true)"
counter="${TMPDIR:-/tmp}/claude-turn-end-${sid:-unknown}"
count="$(cat "$counter" 2>/dev/null || true)"
case "$count" in ''|*[!0-9]*) count=0 ;; esac

cd "$root"

# Guard 2: only run when Python files actually changed this session.
# `git status --porcelain -- '*.py'` covers modified AND untracked files. The
# pattern stays quoted: unquoted, bash expands it against the repo root before
# git sees it, and this check silently stops firing.
changed="$(git status --porcelain -- '*.py' 2>/dev/null || true)"
[ -z "$changed" ] && exit 0

# The 2>&1 wraps the whole group, not just the last command: a checker that
# reports on stderr would otherwise leave the agent a blocked stop and no
# explanation.
if ! output="$(
  {
    uv run mypy src tests \
      && uv run lint-imports \
      && uv run semgrep --config .semgrep --error --quiet
  } 2>&1
)"; then
  if [ "$count" -ge 3 ]; then
    # Give up: an error the agent couldn't fix in 3 tries won't yield to a 4th
    # block. Clear the counter so a later turn gets a fresh budget.
    rm -f "$counter"
    echo "turn-end-check: still red after 3 blocked stops — letting the stop through." >&2
    exit 0
  fi
  echo $((count + 1)) > "$counter"
  echo "The turn-end check failed. Fix these before finishing:" >&2
  echo "$output" >&2
  exit 2
fi

rm -f "$counter"
exit 0
