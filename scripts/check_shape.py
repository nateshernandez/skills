#!/usr/bin/env python3
"""Check the code's shape against the config's `architecture`: module layout and file length.

Usage:
  check_shape.py [FILE ...]          check these files, or every file git sees when none given
  check_shape.py --write-baseline    record today's problems in `architecture.baseline`

A module (each folder in `architecture.modules`) holds only `module_files` at its root and the
folders in `module_folders`; each folder is flat, and its files match that folder's globs. A test
file counts as the file it tests: `ticket-list.test.tsx` is checked as `ticket-list.tsx`. Every
other file matching `sources` stays within `max_lines`. Files matching `exempt` are skipped.

A baseline lets an existing app adopt the shape: a file it lists may keep its place, and keep its
length as long as it doesn't grow; anything new is held to the shape. Prints one line per
problem; exit 1 on a problem.
"""

import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from kit_config import Architecture, Config, ConfigError, load, relative

TEST_SUFFIX_RE = re.compile(r"\.(test|spec)(?=\.[^.]+$)")


class Baseline(NamedTuple):
    lines: dict[str, int]
    shape: frozenset[str]


def main() -> int:
    arguments = sys.argv[1:]
    try:
        config = load()
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    if config.architecture is None:
        print("no `architecture` in the config; nothing to check")
        return 0
    if arguments == ["--write-baseline"]:
        return write_baseline(config)
    if any(argument.startswith("-") for argument in arguments):
        print(__doc__, file=sys.stderr)
        return 1
    paths = [Path(argument).resolve() for argument in arguments] or project_files(config.root)
    problems = check_paths(paths, config)
    for problem in problems:
        print(problem)
    if not problems:
        print(f"ok: {len(paths)} file(s)")
    return 1 if problems else 0


def check_paths(paths: list[Path], config: Config) -> list[str]:
    """One line per problem, each naming the file and the fix."""
    architecture = config.architecture
    assert architecture is not None
    baseline = read_baseline(architecture)
    problems = []
    for path in paths:
        shown_path = relative(path, config.root)
        if not path.is_file() or matches_any(shown_path, architecture.exempt):
            continue
        if shown_path not in baseline.shape and (problem := shape_problem(path, architecture)):
            problems.append(f"{shown_path}: {problem}")
        if problem := length_problem(path, shown_path, architecture, baseline):
            problems.append(f"{shown_path}: {problem}")
    if problems:
        problems.append(f"See {relative(architecture.guide, config.root)} for where code goes.")
    return problems


def shape_problem(path: Path, architecture: Architecture) -> str | None:
    if not path.is_relative_to(architecture.modules):
        return None
    module, *inner = path.relative_to(architecture.modules).parts
    if not inner:
        return f"`{module}` sits beside the modules; put it inside one, or outside the folder"
    if len(inner) == 1:
        return root_file_problem(inner[0], architecture)
    return folder_file_problem(inner, architecture)


def folder_file_problem(inner: list[str], architecture: Architecture) -> str | None:
    folder, *rest = inner
    globs = architecture.module_folders.get(folder)
    if globs is None:
        folders = ", ".join(f"{name}/" for name in architecture.module_folders)
        return f"a module has no `{folder}/`; each file goes in one of {folders}"
    if len(rest) > 1:
        return f"`{folder}/` is flat; a module that needs subfolders is two modules"
    if not any(fnmatch.fnmatchcase(subject_name(rest[0]), glob) for glob in globs):
        return (
            f"`{folder}/` holds {', '.join(globs)}; rename the file for its kind or move it"
            " where its kind belongs"
        )
    return None


def root_file_problem(name: str, architecture: Architecture) -> str | None:
    if subject_name(name) in architecture.module_files:
        return None
    files = ", ".join(architecture.module_files)
    folders = ", ".join(f"{folder}/" for folder in architecture.module_folders)
    return f"a module's root holds only {files}; move it into {folders}"


def length_problem(
    path: Path, shown_path: str, architecture: Architecture, baseline: Baseline
) -> str | None:
    is_test = TEST_SUFFIX_RE.search(path.name) is not None
    if is_test or not matches_any(shown_path, architecture.sources):
        return None
    line_count = count_lines(path)
    allowed = max(architecture.max_lines, baseline.lines.get(shown_path, 0))
    if line_count <= allowed:
        return None
    if allowed > architecture.max_lines:
        return (
            f"grew from {allowed} to {line_count} lines; it's over {architecture.max_lines},"
            " so move code out of it instead of adding"
        )
    return f"{line_count} lines, over {architecture.max_lines}; split it so each file does one job"


def write_baseline(config: Config) -> int:
    architecture = config.architecture
    assert architecture is not None
    if architecture.baseline is None:
        print("set architecture.baseline to the file to write, then rerun", file=sys.stderr)
        return 1
    lines: dict[str, int] = {}
    shape: list[str] = []
    empty = Baseline({}, frozenset())
    for path in project_files(config.root):
        shown_path = relative(path, config.root)
        if matches_any(shown_path, architecture.exempt):
            continue
        if shape_problem(path, architecture):
            shape.append(shown_path)
        if length_problem(path, shown_path, architecture, empty):
            lines[shown_path] = count_lines(path)
    architecture.baseline.parent.mkdir(parents=True, exist_ok=True)
    architecture.baseline.write_text(json.dumps({"lines": lines, "shape": shape}, indent=2) + "\n")
    shown_baseline = relative(architecture.baseline, config.root)
    print(f"wrote {shown_baseline}: {len(lines)} long file(s), {len(shape)} misplaced file(s)")
    return 0


def read_baseline(architecture: Architecture) -> Baseline:
    if architecture.baseline is None or not architecture.baseline.exists():
        return Baseline({}, frozenset())
    raw = json.loads(architecture.baseline.read_text())
    return Baseline(dict(raw["lines"]), frozenset(raw["shape"]))


def project_files(root: Path) -> list[Path]:
    """Tracked files plus new ones git doesn't ignore, so a builder's uncommitted file counts."""
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    paths = (root / name for name in completed.stdout.split("\0") if name)
    return sorted(path for path in paths if path.is_file())


def subject_name(name: str) -> str:
    return TEST_SUFFIX_RE.sub("", name)


def count_lines(path: Path) -> int:
    return len(path.read_text(errors="replace").splitlines())


def matches_any(shown_path: str, globs: tuple[str, ...]) -> bool:
    return any(glob_regex(glob).fullmatch(shown_path) for glob in globs)


def glob_regex(glob: str) -> re.Pattern[str]:
    """A repo-relative glob where `**/` spans folders and `*` stays within one."""
    pattern = ""
    index = 0
    while index < len(glob):
        if glob.startswith("**/", index):
            pattern += "(?:.*/)?"
            index += 3
        elif glob.startswith("**", index):
            pattern += ".*"
            index += 2
        else:
            char = glob[index]
            pattern += {"*": "[^/]*", "?": "[^/]"}.get(char, re.escape(char))
            index += 1
    return re.compile(pattern)


if __name__ == "__main__":
    sys.exit(main())
