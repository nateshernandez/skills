#!/usr/bin/env python3
"""Check that this branch adds at most one date heading to the harness CHANGELOG.

A pull request lands on main on one day, so all of its entries share one heading.

Usage:
  check_branch_dates.py [BASE]   compare against BASE (default: origin/main); exit 1 on problems
"""

import subprocess
import sys
from pathlib import Path

from lint_changelog import CHANGELOG_PATH, DATE_HEADING_RE

DEFAULT_BASE = "origin/main"


def main() -> int:
    arguments = sys.argv[1:]
    if len(arguments) > 1 or (arguments and arguments[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 1
    base = arguments[0] if arguments else DEFAULT_BASE
    base_text = read_base_changelog(base)
    if base_text is None:
        print(f"{base}: no merge base with HEAD; pass a base ref that exists", file=sys.stderr)
        return 1
    problem = find_problem(base_text, CHANGELOG_PATH.read_text())
    if problem:
        print(f"{CHANGELOG_PATH}: {problem}", file=sys.stderr)
        return 1
    print(f"{CHANGELOG_PATH}: ok")
    return 0


def read_base_changelog(base: str) -> str | None:
    repo_root = CHANGELOG_PATH.parents[1]
    merge_base = run_git(repo_root, "merge-base", "HEAD", base)
    if merge_base is None:
        return None
    relative_path = CHANGELOG_PATH.relative_to(repo_root).as_posix()
    return run_git(repo_root, "show", f"{merge_base.strip()}:{relative_path}") or ""


def run_git(repo_root: Path, *arguments: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *arguments], capture_output=True, text=True, check=False
    )
    return result.stdout if result.returncode == 0 else None


def find_problem(base_text: str, branch_text: str) -> str | None:
    new_dates = sorted(date_headings(branch_text) - date_headings(base_text), reverse=True)
    if len(new_dates) <= 1:
        return None
    return (
        f"this branch adds {len(new_dates)} date headings ({', '.join(new_dates)}); "
        f"move every entry under `## {new_dates[0]}` and delete the others"
    )


def date_headings(changelog_text: str) -> set[str]:
    return {
        match.group(1)
        for line in changelog_text.splitlines()
        if (match := DATE_HEADING_RE.match(line.rstrip()))
    }


if __name__ == "__main__":
    sys.exit(main())
