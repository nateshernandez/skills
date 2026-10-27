#!/usr/bin/env python3
"""Land a parallel builder's finished task on the spec's branch.

Usage: land_task.py SPEC_ID TASK_ID BRANCH --line "<progress line>"
BRANCH is the builder's worktree branch. Run from the spec's branch, once per finished task, in
the order the tasks passed. It checks that the task passed in its worktree and that the branch
changed only the task's `files` (and their colocated tests), then replays the branch's commits
onto the current branch, marks the task `passes: true`, appends the progress line, and removes
the worktree and branch. The new tasks.json and progress.md lines are left uncommitted so the
orchestrator commits a whole wave at once. Exit 1, changing nothing, when a check fails or a
commit conflicts.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from kit_config import Config, ConfigError, load
from task_graph import parse_tasks, stray_paths


class Landing(NamedTuple):
    spec_id: str
    task_id: str
    branch: str
    progress_line: str


class LandError(Exception):
    """The task can't be landed yet; the message says why."""


def main() -> int:
    landing = parse_arguments(sys.argv[1:])
    if landing is None:
        print(__doc__, file=sys.stderr)
        return 1
    try:
        config = load()
        land(config, landing)
    except (ConfigError, LandError) as error:
        print(error, file=sys.stderr)
        return 1
    print(f"landed {landing.task_id}; commit tasks.json and progress.md after the wave")
    return 0


def parse_arguments(arguments: list[str]) -> Landing | None:
    if len(arguments) != 5 or arguments[3] != "--line":
        return None
    spec_id, task_id, branch, _, progress_line = arguments
    return Landing(spec_id, task_id, branch, progress_line)


def land(config: Config, landing: Landing) -> None:
    tasks_path = config.specs_dir / landing.spec_id / "tasks.json"
    plan = json.loads(tasks_path.read_text())
    task = next((task for task in plan["tasks"] if task["id"] == landing.task_id), None)
    if task is None:
        message = f"{tasks_path}: no task `{landing.task_id}`"
        raise LandError(message)
    worktree = worktree_for_branch(config.root, landing.branch)
    check_passed_in_worktree(worktree, landing)
    base = git(config.root, "merge-base", "HEAD", landing.branch)
    check_scope(config.root, base, landing, plan)
    commits = git(config.root, "rev-list", "--reverse", f"{base}..{landing.branch}").split()
    cherry_pick(config.root, commits, landing)
    task["passes"] = True
    tasks_path.write_text(json.dumps(plan, indent=2) + "\n")
    progress_path = config.specs_dir / landing.spec_id / "progress.md"
    with progress_path.open("a") as progress_file:
        progress_file.write(f"- **{landing.task_id}** → {landing.progress_line}\n")
    git(config.root, "worktree", "remove", "--force", str(worktree))
    git(config.root, "branch", "-D", landing.branch)


def worktree_for_branch(root: Path, branch: str) -> Path:
    listing = git(root, "worktree", "list", "--porcelain")
    for block in listing.split("\n\n"):
        lines = block.splitlines()
        if f"branch refs/heads/{branch}" in lines:
            return Path(lines[0].removeprefix("worktree "))
    message = f"no worktree has branch `{branch}`; pass the builder's branch"
    raise LandError(message)


def check_passed_in_worktree(worktree: Path, landing: Landing) -> None:
    tasks_path = worktree / "specs" / landing.spec_id / "tasks.json"
    tasks = json.loads(tasks_path.read_text())["tasks"]
    passed = any(task["id"] == landing.task_id and task["passes"] for task in tasks)
    if not passed:
        message = (
            f"{landing.task_id} did not pass its gate in {worktree}; mark_task.py must print passes"
        )
        raise LandError(message)


def check_scope(root: Path, base: str, landing: Landing, plan: dict) -> None:
    graph_task = next(
        task for task in parse_tasks(plan["tasks"]) if task.task_id == landing.task_id
    )
    if not graph_task.files:
        return
    changed = git(root, "diff", "--name-only", f"{base}..{landing.branch}").splitlines()
    if stray := stray_paths(changed, graph_task):
        message = f"{landing.task_id} changed files it did not list in `files`: {', '.join(stray)}"
        raise LandError(message)


def cherry_pick(root: Path, commits: list[str], landing: Landing) -> None:
    for commit in commits:
        picked = subprocess.run(
            ["git", "cherry-pick", commit], cwd=root, capture_output=True, text=True, check=False
        )
        if picked.returncode != 0:
            subprocess.run(["git", "cherry-pick", "--abort"], cwd=root, check=False)
            message = (
                f"{landing.task_id} conflicts with what already landed ({picked.stdout.strip()}):"
                " add a `needs` to the plan, or rebuild it on the new branch tip"
            )
            raise LandError(message)


def git(root: Path, *git_args: str) -> str:
    completed = subprocess.run(
        ["git", *git_args], cwd=root, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        message = f"git {' '.join(git_args)}: {completed.stderr.strip()}"
        raise LandError(message)
    return completed.stdout.strip()


if __name__ == "__main__":
    sys.exit(main())
