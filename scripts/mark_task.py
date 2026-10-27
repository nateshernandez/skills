#!/usr/bin/env python3
"""Mark a task done in specs/<id>/tasks.json, only if the task gate is green with it included.

Usage: mark_task.py SPEC_ID TASK_ID
Runs gate.py's task gate: `check`, then this spec's tests, counting this task's behaviors as
delivered. A task that lists `files` in tasks.json may only have changed those paths (and their
colocated tests); anything else uncommitted fails before the gate runs.
"""

import json
import subprocess
import sys
from pathlib import Path

from gate import acceptance_test_ids, describe_green, format_failure, run_gate
from kit_config import Config, ConfigError, load
from task_graph import parse_tasks, stray_paths


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 1
    spec_id, task_id = sys.argv[1:]
    try:
        config = load()
        tasks_path, plan, task = find_task(config, spec_id, task_id)
    except (ConfigError, TaskError) as error:
        print(error, file=sys.stderr)
        return 1
    if task.get("files") and (stray := stray_changes(config, plan, task_id)):
        print(f"{task_id} changed files it did not list in `files`:", file=sys.stderr)
        print("\n".join(f"  - {path}" for path in stray), file=sys.stderr)
        print("Undo them, or stop and report: the plan's files are wrong.", file=sys.stderr)
        return 1
    result = run_gate(config, spec_id, "task", task_id)
    if not result.is_green:
        print(format_failure(result), file=sys.stderr)
        return 1
    task["passes"] = True
    tasks_path.write_text(json.dumps(plan, indent=2) + "\n")
    print(f"{describe_green(result)}; {summary(task_id, plan['tasks'], tasks_path)}")
    return 0


def stray_changes(config: Config, plan: dict, task_id: str) -> list[str]:
    graph_task = next(task for task in parse_tasks(plan["tasks"]) if task.task_id == task_id)
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=config.root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    changed_paths = [line[3:].split(" -> ")[-1].strip('"') for line in status.splitlines()]
    return stray_paths(changed_paths, graph_task)


class TaskError(Exception):
    """The task can't be gated yet; the message says why."""


def find_task(config: Config, spec_id: str, task_id: str) -> tuple[Path, dict, dict]:
    tasks_path = config.specs_dir / spec_id / "tasks.json"
    if not tasks_path.exists():
        message = f"specs/{spec_id}/tasks.json doesn't exist; plan the spec first"
        raise TaskError(message)
    plan = json.loads(tasks_path.read_text())
    task = next((task for task in plan["tasks"] if task["id"] == task_id), None)
    if task is None:
        known_ids = [task["id"] for task in plan["tasks"]]
        message = f"specs/{spec_id}/tasks.json: no task `{task_id}`; tasks are {known_ids}"
        raise TaskError(message)
    untested_ids = sorted(set(task["covers"]) - set(acceptance_test_ids(config, spec_id)))
    if untested_ids:
        message = f"{task_id} covers {untested_ids}, which have no acceptance test"
        raise TaskError(message)
    return tasks_path, plan, task


def summary(task_id: str, tasks: list[dict], tasks_path: Path) -> str:
    done_count = sum(task["passes"] for task in tasks)
    next_task = next((task for task in tasks if not task["passes"]), None)
    next_line = f"next: {next_task['id']} {next_task['title']}" if next_task else "all tasks pass"
    return f"{task_id} passes ({tasks_path.parent.name}: {done_count}/{len(tasks)}); {next_line}"


if __name__ == "__main__":
    sys.exit(main())
