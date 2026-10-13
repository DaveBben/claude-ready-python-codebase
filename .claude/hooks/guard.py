#!/usr/bin/env python3
"""PreToolUse hook on Bash: refuses commands an agent must never run here.

Usage: guard.py (reads the hook's JSON on stdin) | guard.py --self-test

Refused:
  pip install, python -m pip install, uv pip install: they bypass uv.lock.
  git add -A / --all / . / :/ / *: a blanket add sweeps in scratch files and secrets.
  git commit --no-verify / -n, git push --no-verify, SKIP=<hook> before a
  command, and setting core.hooksPath: each skips the pre-commit hooks.
  uv add of a package PyPI does not have, or whose first release is under
  NEW_PACKAGE_DAYS old: a guard against slopsquatting, where an agent installs a
  hallucinated name that an attacker has registered.

Exit 2 blocks the command and shows Claude the reason on stderr. Unreadable
input exits 0, and so does a PyPI lookup that fails, so a broken hook or network
never blocks unrelated work.

The command is split the way a shell splits it (quotes kept whole; `;`, `&&`,
`|` and newlines end each simple command), and each simple command's program is
found through the wrappers that run another command: `env`, `timeout`, `uv run`,
`python -m`, `bash -c`, `eval` and the like. Quoted data (`git commit -m "..."`) is not
a program, and passes.
"""

import json
import re
import shlex
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path

NEW_PACKAGE_DAYS = 30

PIP = "Do not install with pip: it bypasses uv.lock. Add a dependency with `uv add <pkg>` and build the environment with `uv sync`."
GIT_ADD = "Do not stage with `git add -A`, `--all`, `.` or `*`: a blanket add sweeps in scratch files and secrets. Name each path: git add path/one path/two"
NO_VERIFY = "Do not skip the pre-commit hooks (--no-verify, -n, SKIP=, core.hooksPath). Fix what they report, then commit normally."
MISSING = "`uv add {name}`: PyPI has no package named {name}. Check the name with the user before adding anything; an agent's guessed name is what attackers register."
TOO_NEW = "`uv add {name}`: {name} was first published {days} days ago. A package that new is a slopsquatting risk; ask the user to confirm it and add it themselves."

HEREDOC = re.compile(r"""<<-?\s*['"]?(\w+)['"]?[^\n]*\n.*?\n\1\b""", re.DOTALL)
OPERATOR_CHARS = ";&|()\n"
PLAIN_WRAPPERS = {
    "env",
    "nohup",
    "time",
    "exec",
    "command",
    "nice",
    "sudo",
    "caffeinate",
}
SHELLS = {"bash", "sh", "zsh", "dash"}
PYTHON = re.compile(r"python[\d.]*")
# uv and uvx options that take a separate value; every other option takes none.
UV_VALUE_FLAGS = {
    "--env-file", "--with", "--with-editable", "--with-requirements", "--project",
    "--directory", "--python", "-p", "--package", "--extra", "--group", "--only-group",
    "--no-group", "--index", "--default-index", "--index-url", "--extra-index-url",
    "--find-links", "-f", "--config-file", "--cache-dir", "--config-setting", "-C",
    "--from", "--color", "--allow-insecure-host", "--resolution", "--prerelease",
    "--link-mode", "--exclude-newer", "--python-platform", "--refresh-package",
    "--reinstall-package", "--upgrade-package", "-P", "--keyring-provider",
    "--index-strategy",
}  # fmt: skip
UV_ADD_VALUE_FLAGS = UV_VALUE_FLAGS | {
    "--optional", "-r", "--requirements", "-c", "--constraints", "-m", "--marker",
    "--tag", "--branch", "--rev", "--script", "--bounds",
}  # fmt: skip
INDEX_FLAGS = {
    "--index",
    "--default-index",
    "--index-url",
    "--extra-index-url",
    "--find-links",
    "-f",
}
# Pathspecs that name the whole tree: `.`, `./`, `:/`, `*`.
WHOLE_TREE = {".", ":", "*", ":/*"}
# git commit short options that take a value; letters after one are its value.
COMMIT_VALUE_LETTERS = re.compile(r"[mFCct]")
REQUIREMENT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

# Returns the package's first upload time, None when PyPI has no such package,
# or raises OSError when PyPI cannot be asked.
Lookup = Callable[[str], datetime | None]


def pypi_first_upload(name: str) -> datetime | None:
    url = f"https://pypi.org/pypi/{name}/json"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == HTTPStatus.NOT_FOUND:
            return None
        raise
    uploads = [
        f["upload_time_iso_8601"] for files in data["releases"].values() for f in files
    ]
    if not uploads:
        return None
    return min(datetime.fromisoformat(u) for u in uploads)


def simple_commands(command: str) -> Iterator[list[str]]:
    """Each simple command in `command` as its words, quotes removed."""
    lexer = shlex.shlex(
        HEREDOC.sub("", command), posix=True, punctuation_chars=OPERATOR_CHARS
    )
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:  # unbalanced quotes: fall back to plain words
        tokens = command.split()
    words: list[str] = []
    for token in tokens:
        if token and set(token) <= set(OPERATOR_CHARS):
            if words:
                yield words
            words = []
        else:
            words.append(token)
    if words:
        yield words


def after_options(
    words: list[str], value_flags: set[str] | frozenset[str] = frozenset()
) -> list[str]:
    """`words` past its leading options and NAME=value assignments."""
    i = 0
    while i < len(words) and (
        words[i].startswith("-") or re.fullmatch(r"\w+=.*", words[i])
    ):
        i += 2 if words[i] in value_flags else 1
    return words[i:]


class Guard:
    def __init__(self, lookup: Lookup, now: datetime) -> None:
        self.lookup = lookup
        self.now = now
        self.handlers: dict[str, Callable[[list[str]], str | None]] = {
            **dict.fromkeys(PLAIN_WRAPPERS, self.reason_for),
            **dict.fromkeys(SHELLS, self.shell_reason),
            "timeout": lambda args: self.reason_for(after_options(args)[1:]),
            "uvx": lambda args: self.run_args(
                after_options(args, UV_VALUE_FLAGS), UV_VALUE_FLAGS
            ),
            "uv": self.uv_reason,
            "git": git_reason,
            "eval": lambda args: self.check(" ".join(args)),
            "export": skip_reason,
        }

    def check(self, command: str) -> str | None:
        """Why `command` is refused, or None."""
        for words in simple_commands(command):
            reason = self.reason_for(words)
            if reason:
                return reason
        return None

    def reason_for(self, words: list[str]) -> str | None:
        if skip_reason(words):
            return NO_VERIFY
        words = after_options(words)
        if not words:
            return None
        program, args = Path(words[0]).name, words[1:]
        if re.fullmatch(r"pip3?(\.\d+)?", program):
            return PIP if "install" in args else None
        if PYTHON.fullmatch(program):
            return self.run_args(args, set())
        handler = self.handlers.get(program)
        return handler(args) if handler else None

    def shell_reason(self, args: list[str]) -> str | None:
        """`bash -c 'cmd'` and the like run `cmd`."""
        for i, arg in enumerate(args[:-1]):
            if re.fullmatch(r"-[a-z]*c", arg):
                return self.check(args[i + 1])
        return None

    def run_args(self, args: list[str], value_flags: set[str]) -> str | None:
        """Why `uv run`, `uvx` or `python` with `args` is refused, or None."""
        i = 0
        while i < len(args) and args[i].startswith("-"):
            arg = args[i]
            module = None
            if arg in ("-m", "--module"):
                module = args[i + 1] if i + 1 < len(args) else ""
            elif arg.startswith("-m") and not arg.startswith("--"):
                module = arg[2:]
            if module is not None:
                return PIP if module == "pip" and "install" in args[i + 2 :] else None
            if arg == "-c":
                return None
            i += 2 if arg in value_flags else 1
        return self.reason_for(args[i:])

    def uv_reason(self, args: list[str]) -> str | None:
        rest = after_options(args, UV_VALUE_FLAGS)
        if rest[:2] == ["pip", "install"]:
            return PIP
        if rest[:2] == ["tool", "run"]:
            return self.run_args(rest[2:], UV_VALUE_FLAGS)
        if rest[:1] == ["run"]:
            return self.run_args(rest[1:], UV_VALUE_FLAGS)
        if rest[:1] == ["add"]:
            return self.add_reason(rest[1:])
        return None

    def add_reason(self, args: list[str]) -> str | None:
        """Why `uv add args` is refused: a requirement PyPI lacks or got recently."""
        if any(a.split("=")[0] in INDEX_FLAGS for a in args):
            return None  # another index: PyPI cannot vouch for it either way
        names = []
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("-"):
                i += 2 if arg in UV_ADD_VALUE_FLAGS else 1
                continue
            i += 1
            if "/" in arg or ":" in arg or arg.startswith("."):
                continue  # a path, URL or git source, not a PyPI name
            match = REQUIREMENT_NAME.match(arg)
            if match:
                names.append(re.sub(r"[-_.]+", "-", match.group()).lower())
        for name in names:
            try:
                first = self.lookup(name)
            except (OSError, ValueError, KeyError):
                continue  # PyPI unreachable: uv add will fail or succeed on its own
            if first is None:
                return MISSING.format(name=name)
            days = (self.now - first).days
            if days < NEW_PACKAGE_DAYS:
                return TOO_NEW.format(name=name, days=days)
        return None


def skip_reason(words: list[str]) -> str | None:
    """`SKIP=hook` in a command's leading assignments, or in `export`, skips that pre-commit hook."""
    for word in words:
        if word.startswith("SKIP="):
            return NO_VERIFY
        if not re.fullmatch(r"\w+=.*|-\w*", word):
            return None
    return None


def git_reason(args: list[str]) -> str | None:
    i = 0
    while i < len(args) and args[i].startswith("-"):
        if (
            args[i] == "-c"
            and i + 1 < len(args)
            and args[i + 1].lower().startswith("core.hookspath")
        ):
            return NO_VERIFY
        i += 2 if args[i] in ("-C", "-c") else 1
    sub, rest = args[i : i + 1], args[i + 1 :]
    if sub == ["add"] and any(
        a == "--all"
        or re.fullmatch(r"-[a-zA-Z]*A[a-zA-Z]*", a)
        or a.rstrip("/") in WHOLE_TREE
        for a in rest
    ):
        return GIT_ADD
    if sub in (["commit"], ["push"]) and "--no-verify" in rest:
        return NO_VERIFY
    # -n is --no-verify for commit only (for push it is --dry-run); in -mfoo, foo is the message.
    if sub == ["commit"] and any(
        re.fullmatch(r"-[a-zA-Z]+", a) and "n" in COMMIT_VALUE_LETTERS.split(a[1:])[0]
        for a in rest
    ):
        return NO_VERIFY
    if sub == ["config"] and any(a.lower() == "core.hookspath" for a in rest):
        return NO_VERIFY
    return None


def self_test() -> None:
    now = datetime(2026, 1, 31, tzinfo=UTC)
    known = {
        "requests": datetime(2011, 2, 14, tzinfo=UTC),
        "fresh-pkg": datetime(2026, 1, 21, tzinfo=UTC),
    }

    def lookup(name: str) -> datetime | None:
        if name == "offline":
            raise OSError
        return known.get(name)

    check = Guard(lookup, now).check
    refused = {
        "pip install requests": PIP,
        "python3 -m pip install x": PIP,
        "uv pip install x": PIP,
        "uv run python -m pip install x": PIP,
        "bash -c 'pip install x'": PIP,
        "git add -A": GIT_ADD,
        "git add .": GIT_ADD,
        "cd x && git add --all": GIT_ADD,
        "git commit --no-verify -m x": NO_VERIFY,
        "git commit -nm x": NO_VERIFY,
        "git -c core.hooksPath=/dev/null commit -m x": NO_VERIFY,
        "git add -vA": GIT_ADD,
        "git add ./": GIT_ADD,
        "git add :/": GIT_ADD,
        "git add '*'": GIT_ADD,
        "git commit -anm x": NO_VERIFY,
        "git push --no-verify": NO_VERIFY,
        "SKIP=gitleaks git commit -m x": NO_VERIFY,
        "env SKIP=mypy git push": NO_VERIFY,
        "export SKIP=pytest; git push": NO_VERIFY,
        "git config core.hooksPath /dev/null": NO_VERIFY,
        "eval 'pip install x'": PIP,
        "uv add no-such-pkg": MISSING.format(name="no-such-pkg"),
        "uv add --dev 'Fresh_Pkg>=1.0'": TOO_NEW.format(name="fresh-pkg", days=10),
    }
    for command, reason in refused.items():
        assert check(command) == reason, command
    allowed = [
        "pip list",
        "uv pip list",
        "git add src/a.py",
        'git commit -m "never pip install or git add ."',
        "git commit -m x",
        "git commit -mnew",
        "git push -n origin main",
        "git add -u src",
        "echo SKIP=x",
        "uv add requests",
        "uv add 'requests[socks]>=2' --group dev",
        "uv add offline",
        "uv add ./local-pkg git+https://github.com/a/b",
        "uv add --index https://example.com/simple private-pkg",
        "uv run pytest",
        "cat <<EOF\npip install x\nEOF",
    ]
    for command in allowed:
        assert check(command) is None, command
    print("self-test passed")


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return 0
    try:
        command = json.load(sys.stdin)["tool_input"]["command"]
    except (ValueError, KeyError, TypeError):
        return 0
    reason = Guard(pypi_first_upload, datetime.now(UTC)).check(command)
    if reason:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
