#!/usr/bin/env python3
"""Claude Code hook that gates turns and pull requests on ./check. Usage: gate.py stop | pr | --self-test

  stop  On Stop, when Claude has finished its turn: runs ./check when the work
        tree changed since ./check last passed. A failure blocks the stop once
        and shows Claude the output; when the next stop still fails, it lets
        the turn end and tells the user.
  pr    On PreToolUse: before a command or tool that opens a pull or merge
        request, runs ./check --full in the repository the command runs in (a
        leading `cd X` or `git -C X`), unless the same tree already passed it,
        and refuses the request when it fails. A pass on a branch that changes
        more than DIFF_CAP lines against main asks the user first.

A check that fails and then passes on the same tree has a flaky test: the pass
goes through, and the user is shown the earlier failure.

Fails open: no git, no executable ./check at the repository root, or unreadable
input exits 0.
"""

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

PR_COMMAND = re.compile(r"\b(gh\s+pr|glab\s+mr|tea\s+(pr|pulls))\s+create\b")
PR_TOOL = re.compile(r"create_(pull|merge)_request|(pull|merge)_request_create")
OK = 0  # exit code that lets the turn or the pull request through
BLOCK = 2  # exit code that blocks it and shows Claude the message on stderr
FAILURE_TAIL = 4000  # bytes of a failure's output kept for Claude
FLAKE_TAIL = 1500  # bytes of the earlier failure kept in a flake message
DIFF_CAP = 400  # changed lines past which a pull request asks; review finds fewer defects past 200 to 400


def git(d: str, *args: str) -> bytes | None:
    r = subprocess.run(["git", "-C", d, *args], capture_output=True, check=False)
    return r.stdout if r.returncode == 0 else None


def words(cmd: str) -> list[str]:
    try:
        return shlex.split(cmd)
    except ValueError:
        return cmd.split()


CMD_START = {"(", "{", "&&", "||", ";", "|", "&"}  # a simple command begins after these


def where(cmd: str, cwd: str) -> str:
    """The directory a command runs in: each leading `cd X` or `git -C X`, in order.

    A `cd` counts when it starts a simple command (first token, or right after a
    shell operator like `(` or `&&`), so `( cd x && ... )` and `cd a && cd b` both
    resolve, applied left to right.
    """
    w = words(cmd)
    for i, t in enumerate(w[:-1]):
        starts_command = i == 0 or w[i - 1] in CMD_START
        if (t == "cd" and starts_command) or (
            t == "-C" and i > 0 and w[i - 1] == "git"
        ):
            target = os.path.expandvars(Path(w[i + 1].rstrip(";")).expanduser())
            cwd = str(Path(cwd) / target)
    return cwd


def tree_state(root: str) -> str:
    names = [
        n.decode()
        for n in (
            git(root, "ls-files", "--others", "--exclude-standard", "-z") or b""
        ).split(b"\0")
        if n
    ]
    parts = [
        git(root, "rev-parse", "HEAD"),
        git(root, "diff", "HEAD", "--binary"),
        "\0".join(names).encode(),
        git(root, "hash-object", "--", *names) if names else b"",
    ]
    return hashlib.sha1(
        b"\0".join(p or b"" for p in parts), usedforsecurity=False
    ).hexdigest()


def read(path: Path) -> str:
    try:
        return path.read_text()
    except OSError:
        return ""


def check(root: str, args: list[str], stamp: str) -> tuple[str | None, str | None]:
    """Runs ./check with args unless this tree already passed.

    Returns (the output of a failure or None, a flake message or None).

    shortcut: the stamp files are read-then-written with no lock, so two hooks
    running at once, or a tree edited mid-run, can stamp a tree as passed that
    was never checked. Assumes one checker at a time; add a lock if the gate is
    ever driven by concurrent agents.
    """
    git_path = git(root, "rev-parse", "--git-path", stamp) or b""
    path = Path(root) / git_path.decode().strip()
    failed = path.with_name(path.name + "-failed")
    key = tree_state(root)
    if read(path) == key:
        return None, None
    r = subprocess.run(
        ["./check", *args], cwd=root, capture_output=True, text=True, check=False
    )
    if r.returncode == 0:
        path.write_text(key)
        earlier = read(failed)
        if earlier.startswith(key + "\n"):
            failed.unlink()
            return None, (
                f"./check {' '.join(args)}".strip()
                + " failed and then passed on the same tree, so a test "
                "is flaky. Earlier failure:\n" + earlier[len(key) + 1 :][-FLAKE_TAIL:]
            )
        return None, None
    out = (r.stdout + r.stderr)[-FAILURE_TAIL:]
    failed.write_text(key + "\n" + out)
    return out, None


def passed(flake: str | None) -> tuple[int, str, str]:
    """The OK result, carrying a flake message to the user when there is one."""
    return OK, json.dumps({"systemMessage": flake}) if flake else "", ""


def changed_lines(root: str) -> int:
    """Lines the branch adds and removes against main, uv.lock left out; 0 with no main."""
    base = git(root, "merge-base", "HEAD", "main") or git(
        root, "merge-base", "HEAD", "origin/main"
    )
    if not base:
        return 0
    rows = (
        git(root, "diff", "--numstat", base.decode().strip(), "HEAD") or b""
    ).decode()
    n = 0
    for row in rows.splitlines():
        added, removed, path = row.split("\t", 2)
        if added.isdigit() and removed.isdigit() and Path(path).name != "uv.lock":
            n += int(added) + int(removed)
    return n


def too_big(root: str, flake: str | None) -> tuple[int, str, str] | None:
    """An ask for a branch over DIFF_CAP changed lines, else None."""
    n = changed_lines(root)
    if n <= DIFF_CAP:
        return None
    ask = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": f"This branch changes {n} lines against main, over the "
        f"{DIFF_CAP}-line cap for one pull request. Approve only when it cannot be split "
        "into slices that each ship alone.",
    }
    out: dict[str, object] = {"hookSpecificOutput": ask}
    if flake:
        out["systemMessage"] = flake
    return OK, json.dumps(out), ""


def gate(mode: str, inp: dict[str, object]) -> tuple[int, str, str]:
    """Returns (exit code, stdout, stderr) for one hook call."""
    cwd = str(inp.get("cwd") or Path.cwd())
    tool = str(inp.get("tool_name", ""))
    tool_input = inp.get("tool_input")
    command = str(
        (tool_input if isinstance(tool_input, dict) else {}).get("command", "")
    )
    if mode == "pr":
        cwd = where(command, cwd)
    top = git(cwd, "rev-parse", "--show-toplevel")
    is_pr = (tool == "Bash" and PR_COMMAND.search(command)) or PR_TOOL.search(tool)
    if (
        not top
        or not os.access(Path(top.decode().strip()) / "check", os.X_OK)
        or (mode == "pr" and not is_pr)
    ):
        return OK, "", ""
    root = top.decode().strip()
    if mode == "stop":
        out, flake = check(root, [], "guardrails-check")
        if out is None:
            return passed(flake)
        if inp.get("stop_hook_active"):
            return (
                OK,
                json.dumps(
                    {"systemMessage": "./check still fails; the turn ended anyway."}
                ),
                "",
            )
        return (
            BLOCK,
            "",
            "./check failed. Fix the cause; never silence a check to pass it.\n" + out,
        )
    out, flake = check(root, ["--full"], "guardrails-full")
    if out is None:
        return too_big(root, flake) or passed(flake)
    return (
        BLOCK,
        "",
        "./check --full failed, so the pull request was not opened. Fix the cause, then open it again.\n"
        + out,
    )


def _run(cwd: str, *a: str) -> None:
    subprocess.run(a, cwd=cwd, check=True, capture_output=True)


def _write(path: str, text: str) -> None:
    Path(path).write_text(text)


def _executable(path: str, text: str) -> None:
    Path(path).write_text(text)
    Path(path).chmod(0o755)


def _repo(parent: str, check_body: str) -> str:
    """A fresh git repository under parent whose executable ./check runs check_body."""

    d = tempfile.mkdtemp(dir=parent)
    _run(d, "git", "init", "-q", d)
    _executable(f"{d}/check", "#!/bin/sh\n" + check_body)
    return d


def self_test() -> None:
    # where() resolves the directory a PR command runs in.
    assert where("cd x && gh pr create", "/a") == "/a/x", "a leading cd"
    assert where("( cd x && gh pr create )", "/a") == "/a/x", "a cd inside a subshell"
    assert where("cd x && cd y && gh pr create", "/a") == "/a/x/y", (
        "chained cd, in order"
    )
    assert where("git -C x pr", "/a") == "/a/x", "git -C"
    # One parent dir holds every test repo, so the single context manager cleans
    # them all up; nothing is left in TMPDIR after the run.
    with tempfile.TemporaryDirectory() as parent:
        _scenarios(parent)
        _cap_scenario(parent)
    print("self-test passed")


def _cap_scenario(parent: str) -> None:
    t = _repo(parent, "exit 0\n")

    def git_t(*a: str) -> None:
        _run(t, "git", "-c", "user.name=t", "-c", "user.email=t@t", *a)

    def pr() -> tuple[int, str, str]:
        return gate(
            "pr",
            {"cwd": t, "tool_name": "Bash", "tool_input": {"command": "gh pr create"}},
        )

    git_t("checkout", "-q", "-b", "main")
    git_t("add", "check")
    git_t("commit", "-q", "-m", "x")
    git_t("checkout", "-q", "-b", "big")
    _write(f"{t}/big.txt", "x\n" * (DIFF_CAP + 1))
    git_t("add", "big.txt")
    git_t("commit", "-q", "-m", "big")
    code, out, _ = pr()
    assert code == OK, "a branch over the cap is not refused"
    assert '"ask"' in out, "a branch over the cap asks"
    git_t("checkout", "-q", "main")
    assert pr()[1] == "", "a branch under the cap does not ask"


def _scenarios(parent: str) -> None:
    t = tempfile.mkdtemp(dir=parent)

    def run(*a: str) -> None:
        _run(t, *a)

    def write(path: str, text: str) -> None:
        _write(path, text)

    def executable(path: str, text: str) -> None:
        _executable(path, text)

    def runs() -> int:
        return len(Path(f"{t}/.git/runs").read_text().splitlines())

    def pr(cmd: str, tool: str = "Bash") -> int:
        return gate(
            "pr", {"cwd": t, "tool_name": tool, "tool_input": {"command": cmd}}
        )[0]

    def repo(check_body: str) -> str:
        return _repo(parent, check_body)

    run("git", "init", "-q", "-b", "main")
    assert gate("stop", {"cwd": t})[0] == OK, "no ./check passes"
    # ./check counts its runs and fails while the file `red` exists or new.txt says bad.
    executable(
        f"{t}/check",
        "#!/bin/sh\necho run >> .git/runs\n"
        '[ ! -e red ] && ! grep -qs bad new.txt || { echo "lint: bad"; exit 1; }\n',
    )
    run("git", "add", "check")
    run("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x")
    assert gate("stop", {"cwd": t})[0] == OK, "green tree passes"
    assert runs() == 1, "green tree ran ./check once"
    assert gate("stop", {"cwd": t})[0] == OK, "unchanged tree passes"
    assert runs() == 1, "unchanged tree is not checked again"
    write(f"{t}/red", "x")
    code, _, err = gate("stop", {"cwd": t})
    assert code == BLOCK, "a failure blocks the stop"
    assert "lint: bad" in err, "and shows the output"
    code, out, _ = gate("stop", {"cwd": t, "stop_hook_active": True})
    assert code == OK, "the second failure lets the turn end"
    assert "still fails" in out, "and tells the user"
    assert pr("gh pr create --fill") == BLOCK, "gh pr create on a red tree is refused"
    assert pr("glab mr create") == BLOCK, "glab mr create"
    assert pr("", "mcp__github__create_pull_request") == BLOCK, (
        "an MCP tool that opens a pull request"
    )
    assert pr("gh pr list") == OK, "other gh commands pass"
    Path(f"{t}/red").unlink()
    assert pr("gh pr create --fill") == OK, "green tree opens the pull request"
    write(f"{t}/new.txt", "ok")
    assert gate("stop", {"cwd": t})[0] == OK, "a new untracked file that passes"
    write(f"{t}/new.txt", "bad")
    assert gate("stop", {"cwd": t})[0] == BLOCK, (
        "an edit to an untracked file is checked again"
    )
    Path(f"{t}/new.txt").unlink()
    o = repo("exit 1\n")  # a second repository whose ./check always fails
    assert pr(f"cd {o}; gh pr create --fill") == BLOCK, (
        "cd then gh pr create checks that directory"
    )
    os.environ["GATE_WT"] = o
    assert pr("cd $GATE_WT && gh pr create --fill") == BLOCK, (
        "a variable in cd is expanded"
    )
    # a third repository whose ./check fails on its first run only
    f = repo('echo run >> .git/runs\n[ "$(wc -l < .git/runs)" -gt 1 ]\n')
    assert gate("stop", {"cwd": f})[0] == BLOCK, "the first run fails"
    code, out, _ = gate("stop", {"cwd": f})
    assert code == OK, "a pass on the tree that failed"
    assert "flaky" in out, "is reported as flaky"
    print("self-test passed")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        sys.exit(0)
    try:
        hook_input = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    code, out, err = gate(sys.argv[1] if len(sys.argv) > 1 else "", hook_input)
    sys.stdout.write(out)
    sys.stderr.write(err)
    sys.exit(code)
