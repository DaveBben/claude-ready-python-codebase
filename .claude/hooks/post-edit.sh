#!/usr/bin/env bash
# PostToolUse hook (matcher: Edit|Write|MultiEdit). Exit 2 feeds stderr back
# to the agent, closing the loop edit -> check -> correct in the same turn.
#
#   *.py            ruff --fix + format, then re-check. Only UNFIXABLE findings
#                   reach the agent. mypy/pytest need the whole package and run
#                   at turn end (./check, through gate.py) and on push.
#   pyproject.toml  uv lock --check. A hand-edited dependency silently desyncs
#                   uv.lock; the agent must use uv add / uv remove instead.
#
# Only files inside THIS repo: the session can edit other working dirs, and
# this repo's rules must not be enforced there.
set -euo pipefail

root="${CLAUDE_PROJECT_DIR:-.}"
file="$(python3 -c 'import json,sys; print((json.load(sys.stdin).get("tool_input") or {}).get("file_path",""))' 2>/dev/null || true)"
case "$file" in "$root"/*) ;; *) exit 0 ;; esac
[ -f "$file" ] || exit 0

case "$file" in
  *.py)
    # Venv binary directly: `uv run` re-checks the environment on every call.
    ruff=("$root/.venv/bin/ruff"); [ -x "${ruff[0]}" ] || ruff=(uv run --project "$root" ruff)
    # --ignore F401: an import added one edit before its first use must survive; ./check catches it unused.
    "${ruff[@]}" check --fix --ignore F401 --force-exclude "$file" >/dev/null 2>&1 || true
    "${ruff[@]}" format --force-exclude "$file" >/dev/null 2>&1 || true
    # ruff exits 1 for findings; anything else is ruff itself failing (report, don't block).
    set +e; output="$("${ruff[@]}" check --ignore F401 --force-exclude "$file" 2>&1)"; code=$?; set -e
    if [ "$code" -eq 1 ]; then
      echo "ruff found issues in $file that need a real fix (not auto-fixable):" >&2
      echo "$output" >&2
      exit 2
    elif [ "$code" -ne 0 ]; then
      echo "post-edit hook: ruff failed to run (exit $code):" >&2
      echo "$output" >&2
    fi
    ;;
  "$root"/pyproject.toml)
    cd "$root"
    if ! output="$(uv lock --check 2>&1)"; then
      echo "pyproject.toml no longer matches uv.lock:" >&2
      echo "$output" >&2
      echo "Change dependencies with 'uv add <pkg>' / 'uv remove <pkg>', never by hand." >&2
      echo "If this edit was not a dependency change, run 'uv lock' to regenerate." >&2
      exit 2
    fi
    ;;
esac
exit 0
