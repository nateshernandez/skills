#!/usr/bin/env python3
"""Get a parallel builder's git worktree ready to build: run `build.worktree_setup` in it.

Usage: prepare_worktree.py
A fresh worktree has the tracked files and nothing else, so no dependencies and no local env
files. `build.worktree_setup` is the command that adds them; it runs from the worktree's root with
KIT_MAIN_ROOT set to the main checkout, for a command like `cp "$KIT_MAIN_ROOT/.env" .env`.
Prints `wave` when run in a worktree, `not a worktree` otherwise; exit 1 when the setup fails.
"""

import os
import subprocess
import sys

from kit_config import ConfigError, linked_worktree_root, load, main_checkout_root, project_root


def main() -> int:
    if sys.argv[1:]:
        print(__doc__, file=sys.stderr)
        return 1
    root = project_root()
    if linked_worktree_root(root) is None:
        print("not a worktree; nothing to prepare")
        return 0
    try:
        setup = load(root).build.worktree_setup
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    if setup:
        step_env = {**os.environ, "KIT_MAIN_ROOT": str(main_checkout_root(root))}
        completed = subprocess.run(setup, shell=True, cwd=root, env=step_env, check=False)
        if completed.returncode != 0:
            print(f"build.worktree_setup failed: {setup}", file=sys.stderr)
            return 1
    print(
        "wave: a parallel build. Return your progress line; leave progress.md to the orchestrator"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
