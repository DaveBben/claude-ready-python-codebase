#!/usr/bin/env python3
"""Claude Code hook for the guardrails skill. Usage: gate.py stop | pr | --self-test

  stop  On Stop, when Claude has finished its turn: runs ./check when the work
        tree changed since ./check last passed. A failure blocks the stop once
        and shows Claude the output; when the next stop still fails, it lets
        the turn end and tells the user.
  pr    On PreToolUse: before a command or tool that opens a pull or merge
        request, runs ./check --full in the repository the command runs in (a
        leading `cd X` or `git -C X`), unless the same tree already passed it,
        and refuses the request when it fails.

A check that fails and then passes on the same tree has a flaky test: the pass
goes through, and the user is shown the earlier failure.

Fails open: no git, no executable ./check at the repository root, or unreadable
input exits 0.
"""
import hashlib, json, os, re, shlex, subprocess, sys

PR_COMMAND = re.compile(r"\b(gh\s+pr|glab\s+mr|tea\s+(pr|pulls))\s+create\b")
PR_TOOL = re.compile(r"create_(pull|merge)_request|(pull|merge)_request_create")


def git(d, *args):
    r = subprocess.run(["git", "-C", d, *args], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def words(cmd):
    try:
        return shlex.split(cmd)
    except ValueError:
        return cmd.split()


def where(cmd, cwd):
    """The directory a command runs in: a leading `cd X` or `git -C X`, else cwd."""
    w = words(cmd)
    for i, t in enumerate(w[:-1]):
        if (t == "cd" and i == 0) or (t == "-C" and i > 0 and w[i - 1] == "git"):
            cwd = os.path.join(cwd, os.path.expandvars(os.path.expanduser(w[i + 1].rstrip(";"))))
    return cwd


def tree_state(root):
    names = [n.decode() for n in (git(root, "ls-files", "--others", "--exclude-standard", "-z") or b"").split(b"\0") if n]
    parts = [git(root, "rev-parse", "HEAD"), git(root, "diff", "HEAD", "--binary"), "\0".join(names).encode(),
             git(root, "hash-object", "--", *names) if names else b""]
    return hashlib.sha1(b"\0".join(p or b"" for p in parts)).hexdigest()


def read(path):
    try:
        return open(path).read()
    except OSError:
        return ""


def check(root, args, stamp):
    """Runs ./check with args unless this tree already passed.

    Returns (the output of a failure or None, a flake message or None)."""
    path = os.path.join(root, git(root, "rev-parse", "--git-path", stamp).decode().strip())
    failed = path + "-failed"
    key = tree_state(root)
    if read(path) == key:
        return None, None
    r = subprocess.run(["./check", *args], cwd=root, capture_output=True, text=True)
    if r.returncode == 0:
        open(path, "w").write(key)
        earlier = read(failed)
        if earlier.startswith(key + "\n"):
            os.remove(failed)
            return None, (f"./check {' '.join(args)}".strip() + " failed and then passed on the same tree, so a test "
                          "is flaky. Earlier failure:\n" + earlier[len(key) + 1:][-1500:])
        return None, None
    out = (r.stdout + r.stderr)[-4000:]
    open(failed, "w").write(key + "\n" + out)
    return out, None


def gate(mode, inp):
    """Returns (exit code, stdout, stderr) for one hook call."""
    cwd = inp.get("cwd") or os.getcwd()
    tool = inp.get("tool_name", "")
    command = (inp.get("tool_input") or {}).get("command", "")
    if mode == "pr":
        cwd = where(command, cwd)
    top = git(cwd, "rev-parse", "--show-toplevel")
    if not top:
        return 0, "", ""
    root = top.decode().strip()
    if not os.access(os.path.join(root, "check"), os.X_OK):
        return 0, "", ""
    if mode == "stop":
        out, flake = check(root, [], "guardrails-check")
        if out is None:
            return 0, json.dumps({"systemMessage": flake}) if flake else "", ""
        if inp.get("stop_hook_active"):
            return 0, json.dumps({"systemMessage": "./check still fails; the turn ended anyway."}), ""
        return 2, "", "./check failed. Fix the cause; never silence a check to pass it.\n" + out
    if not ((tool == "Bash" and PR_COMMAND.search(command)) or PR_TOOL.search(tool)):
        return 0, "", ""
    out, flake = check(root, ["--full"], "guardrails-full")
    if out is None:
        return 0, json.dumps({"systemMessage": flake}) if flake else "", ""
    return 2, "", "./check --full failed, so the pull request was not opened. Fix the cause, then open it again.\n" + out


def self_test():
    import tempfile
    t = tempfile.mkdtemp()
    run = lambda *a: subprocess.run(a, cwd=t, check=True, capture_output=True)
    run("git", "init", "-q", "-b", "main")
    assert gate("stop", {"cwd": t})[0] == 0, "no ./check passes"
    # ./check counts its runs and fails while the file `red` exists or new.txt says bad.
    open(f"{t}/check", "w").write('#!/bin/sh\necho run >> .git/runs\n'
                                  '[ ! -e red ] && ! grep -qs bad new.txt || { echo "lint: bad"; exit 1; }\n')
    os.chmod(f"{t}/check", 0o755)
    run("git", "add", "check")
    run("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x")
    runs = lambda: len(open(f"{t}/.git/runs").readlines())
    assert gate("stop", {"cwd": t})[0] == 0 and runs() == 1, "green tree passes"
    assert gate("stop", {"cwd": t})[0] == 0 and runs() == 1, "unchanged tree is not checked again"
    open(f"{t}/red", "w").write("x")
    code, _, err = gate("stop", {"cwd": t})
    assert code == 2 and "lint: bad" in err, "a failure blocks the stop and shows the output"
    code, out, _ = gate("stop", {"cwd": t, "stop_hook_active": True})
    assert code == 0 and "still fails" in out, "the second failure lets the turn end"
    pr = lambda cmd, tool="Bash": gate("pr", {"cwd": t, "tool_name": tool, "tool_input": {"command": cmd}})[0]
    assert pr("gh pr create --fill") == 2, "gh pr create on a red tree is refused"
    assert pr("glab mr create") == 2, "glab mr create"
    assert pr("", "mcp__github__create_pull_request") == 2, "an MCP tool that opens a pull request"
    assert pr("gh pr list") == 0, "other gh commands pass"
    os.remove(f"{t}/red")
    assert pr("gh pr create --fill") == 0, "green tree opens the pull request"
    open(f"{t}/new.txt", "w").write("ok")
    assert gate("stop", {"cwd": t})[0] == 0, "a new untracked file that passes"
    open(f"{t}/new.txt", "w").write("bad")
    assert gate("stop", {"cwd": t})[0] == 2, "an edit to an untracked file is checked again"
    os.remove(f"{t}/new.txt")
    o = tempfile.mkdtemp()  # a second repository whose ./check always fails
    subprocess.run(["git", "init", "-q", o], check=True)
    open(f"{o}/check", "w").write("#!/bin/sh\nexit 1\n")
    os.chmod(f"{o}/check", 0o755)
    assert pr(f"cd {o}; gh pr create --fill") == 2, "cd then gh pr create checks that directory"
    os.environ["GATE_WT"] = o
    assert pr("cd $GATE_WT && gh pr create --fill") == 2, "a variable in cd is expanded"
    f = tempfile.mkdtemp()  # a third repository whose ./check fails on its first run only
    subprocess.run(["git", "init", "-q", f], check=True)
    open(f"{f}/check", "w").write('#!/bin/sh\necho run >> .git/runs\n[ "$(wc -l < .git/runs)" -gt 1 ]\n')
    os.chmod(f"{f}/check", 0o755)
    assert gate("stop", {"cwd": f})[0] == 2, "the first run fails"
    code, out, _ = gate("stop", {"cwd": f})
    assert code == 0 and "flaky" in out, "a pass on the tree that failed is reported as flaky"
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
