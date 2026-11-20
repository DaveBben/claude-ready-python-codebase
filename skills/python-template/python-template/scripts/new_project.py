#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Make a new project from the bundled template.

    uv run new_project.py <target-dir> <import_name> <description> <copyright-holder>

<import_name> is the package's import name, such as my_project. The
distribution name (my-project) and the base exception prefix (MyProject) come
from it. The project is built in a temporary directory beside the target and
moved into place only once it is complete, so a failure leaves nothing behind.
The target must not exist yet or be an empty directory.
Run `new_project.py --self-test` to check the script itself.
"""

import argparse
import datetime
import keyword
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "project"
OLD = ("example_project", "example-project", "ExampleProject")
OLD_DESCRIPTION = "A template python codebase that is designed to be AI first"
README_PLACEHOLDER = "<!-- What it does and who it is for, in 1 to 3 sentences. -->"
LEFTOVER = re.compile(
    r"example.project|ExampleProject|" + re.escape(OLD_DESCRIPTION), re.IGNORECASE
)
# Local state a developer's checkout of the template may hold; never copied.
SKIP = shutil.ignore_patterns(
    ".venv",
    "__pycache__",
    "*.py[cod]",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".hypothesis",
    ".import_linter_cache",
    ".coverage",
    "htmlcov",
    "mutants",
    ".DS_Store",
    "settings.local.json",
    "worktrees",
)


def names(import_name: str) -> tuple[str, str, str]:
    """The 3 spellings of a project name, in the order of OLD."""
    if not re.fullmatch(
        r"[a-z][a-z0-9]*(_[a-z0-9]+)*", import_name
    ) or keyword.iskeyword(import_name):
        raise ValueError(
            f"{import_name!r} is not a lowercase Python identifier with single inner underscores, such as my_project"
        )
    if import_name in sys.stdlib_module_names:
        raise ValueError(
            f"{import_name!r} would shadow the standard-library module of that name"
        )
    if LEFTOVER.search(import_name):
        raise ValueError(f"{import_name!r} contains the template's own name")
    camel = "".join(part.capitalize() for part in import_name.split("_"))
    return import_name, import_name.replace("_", "-"), camel


def one_line(label: str, value: str) -> str:
    # It lands in a TOML string, a docstring and Markdown, so keep it plain.
    if not value.strip() or re.search(r'["\\\n\r]', value):
        raise ValueError(
            f"the {label} must be one non-empty line with no quotes or backslashes"
        )
    return value.strip()


def fill(
    root: Path, import_name: str, description: str, holder: str, template: Path
) -> None:
    """Copy template to root and make it the named project."""
    new = names(import_name)
    shutil.copytree(template, root, symlinks=True, ignore=SKIP)
    # A plugin install copies symlinks as plain files; ./check needs this one a link.
    link = root / "CLAUDE.md"
    link.unlink()
    link.symlink_to("AGENTS.md")
    (root / "src" / OLD[0]).rename(root / "src" / new[0])
    tests = root / "tests" / "unit"
    (tests / f"test_{OLD[0]}.py").rename(tests / f"test_{new[0]}.py")
    year = datetime.datetime.now(tz=datetime.UTC).year
    left = []
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        raw = path.read_bytes()
        try:
            text = raw.decode()
        except UnicodeDecodeError:
            if LEFTOVER.search(raw.decode("latin-1")):
                left.append(str(path.relative_to(root)))
            continue
        for old, repl in zip(OLD, new, strict=True):
            text = text.replace(old, repl)
        text = text.replace(OLD_DESCRIPTION, description).replace(
            README_PLACEHOLDER, description
        )
        if path.name == "LICENSE":
            text = re.sub(
                r"Copyright \(c\) \d{4} .*", f"Copyright (c) {year} {holder}", text
            )
        if text != raw.decode():
            path.write_bytes(text.encode())
        if LEFTOVER.search(text) or LEFTOVER.search(str(path.relative_to(root))):
            left.append(str(path.relative_to(root)))
    if left:
        raise RuntimeError(f"old name left in: {', '.join(left)}")
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)


def create(
    target: Path,
    import_name: str,
    description: str,
    holder: str,
    template: Path = TEMPLATE,
) -> None:
    description = one_line("description", description)
    holder = one_line("copyright holder", holder)
    names(import_name)
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise FileExistsError(
            f"{target} exists and is not an empty directory; pick a new one"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=".new_project-") as tmp:
        built = Path(tmp) / "p"
        fill(built, import_name, description, holder, template)
        if target.exists():
            target.rmdir()
        built.rename(target)


def self_test() -> None:
    assert names("my_project") == ("my_project", "my-project", "MyProject")
    for bad in (
        "My_Project",
        "my-project",
        "my_project_",
        "my__project",
        "1x",
        "class",
        "logging",
        "my_example_project",
        "",
    ):
        try:
            names(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} was accepted")
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        # Built from a dereferenced copy, as a plugin install delivers it.
        plain = t / "plain"
        shutil.copytree(TEMPLATE, plain, ignore=SKIP)
        assert not (plain / "CLAUDE.md").is_symlink()
        p = t / "p"
        create(p, "acme_tools", "Tools for Acme.", "Ada Lovelace", plain)
        assert (
            (p / "src" / "acme_tools" / "__init__.py")
            .read_text()
            .startswith('"""Tools for Acme.')
        )
        assert (p / "tests" / "unit" / "test_acme_tools.py").is_file()
        assert (p / "CLAUDE.md").readlink() == Path("AGENTS.md")
        assert (
            "AcmeToolsError" in (p / "src" / "acme_tools" / "exceptions.py").read_text()
        )
        pyproject = (p / "pyproject.toml").read_text()
        assert 'name = "acme-tools"' in pyproject
        assert 'description = "Tools for Acme."' in pyproject
        assert "Ada Lovelace" in (p / "LICENSE").read_text()
        assert "Tools for Acme." in (p / "README.md").read_text()
        assert (p / ".git").is_dir()
        for args, error in (
            ((p, "acme_tools", "x", "y"), FileExistsError),
            ((p / "LICENSE", "acme_tools", "x", "y"), FileExistsError),
            ((t / "q", "acme_tools", 'say "hi"', "y"), ValueError),
        ):
            try:
                create(*args)
            except error:
                continue
            raise AssertionError(f"{args} was accepted")
        # A leftover old name fails the run and leaves the target absent.
        (plain / "docs.md").write_text("see EXAMPLE_PROJECT\n")
        try:
            create(t / "r", "acme_tools", "x", "y", plain)
        except RuntimeError:
            assert not (t / "r").exists(), "a failed run left the target behind"
            assert not list(t.glob(".new_project-*")), (
                "a failed run left its build directory"
            )
        else:
            raise AssertionError("a leftover old name was not reported")
    print("self-test passed")


def main() -> None:
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("target", type=Path)
    parser.add_argument("import_name")
    parser.add_argument("description")
    parser.add_argument("holder")
    a = parser.parse_args()
    try:
        create(a.target, a.import_name, a.description, a.holder)
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as e:
        sys.exit(f"new_project.py: {e}")
    print(f"created {a.target}")


if __name__ == "__main__":
    main()
