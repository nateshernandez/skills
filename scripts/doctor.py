#!/usr/bin/env python3
"""Check that this project is ready for kit, one line per check with the fix for each failure.

Usage: doctor.py [--run-check]
  --run-check   also run the config's `check` command, which must pass before the first build

Checks: Python version, git, the config, the folders kit writes to, the commands the config
names, and (with --run-check) a green `check` on the current tree.
"""

import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from kit_config import CONFIG_PATH, Config, ConfigError, load, project_root

MIN_PYTHON = (3, 11)


class Result(NamedTuple):
    is_ok: bool
    line: str


def passed(line: str) -> Result:
    return Result(is_ok=True, line=line)


def failed(line: str) -> Result:
    return Result(is_ok=False, line=line)


def main() -> int:
    arguments = sys.argv[1:]
    if arguments not in ([], ["--run-check"]):
        print(__doc__, file=sys.stderr)
        return 1
    root = project_root()
    results = [check_python(), check_git(root)]
    try:
        config = load(root)
    except ConfigError as error:
        results.append(failed(f"config: {error}"))
        config = None
    else:
        results.append(passed(f"config: {CONFIG_PATH} loads"))
    if config is not None:
        results += check_folders(config)
        results += check_commands(config)
        if arguments == ["--run-check"]:
            results.append(run_check(config))
    for result in results:
        print(f"{'ok  ' if result.is_ok else 'FAIL'} {result.line}")
    return 0 if all(result.is_ok for result in results) else 1


def check_python() -> Result:
    version = ".".join(map(str, sys.version_info[:3]))
    if sys.version_info >= MIN_PYTHON:
        return passed(f"python: {version}")
    needed = ".".join(map(str, MIN_PYTHON))
    return failed(f"python: {version}; kit's scripts need {needed}+ as `python3`")


def check_git(root: Path) -> Result:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    if completed.returncode == 0:
        return passed(f"git: {root} has commits")
    return failed(f"git: {root} needs to be a git repo with at least one commit")


def check_folders(config: Config) -> list[Result]:
    return [
        passed(f"folder: {folder_name}/")
        if path.is_dir()
        else failed(f"folder: {folder_name}/ missing; /kit:setup creates it")
        for path in (config.specs_dir, config.decisions_dir)
        if (folder_name := path.relative_to(config.root).as_posix())
    ]


def check_commands(config: Config) -> list[Result]:
    named_commands = {
        "check": config.check,
        "check_full": config.check_full,
        "tests.run": config.tests.run,
        "app.serve": config.app.serve if config.app else None,
        "screenshots": config.screenshots,
        "audit": config.audit,
        "format.run": config.format.run if config.format else None,
        "lint.run": config.lint.run if config.lint else None,
    }
    return [
        check_program(name, command, config.root)
        for name, command in named_commands.items()
        if command is not None
    ]


def check_program(name: str, command: str, root: Path) -> Result:
    # Leading `NAME=value` words set the environment; the program comes after them.
    words = shlex.split(command)
    program = next((word for word in words if "=" not in word), words[0])
    is_found = (root / program).exists() if "/" in program else shutil.which(program) is not None
    if is_found:
        return passed(f"{name}: `{program}` found")
    return failed(f"{name}: `{program}` not found; install it or fix the command")


def run_check(config: Config) -> Result:
    print(f"running `{config.check}` ...", flush=True)
    completed = subprocess.run(
        config.check, shell=True, cwd=config.root, capture_output=True, text=True, check=False
    )
    if completed.returncode == 0:
        return passed("check: green on the current tree")
    last_lines = "\n     ".join((completed.stdout + completed.stderr).strip().splitlines()[-15:])
    return failed(f"check: red; every task would fail. Fix it first:\n     {last_lines}")


if __name__ == "__main__":
    sys.exit(main())
