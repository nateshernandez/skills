#!/usr/bin/env python3
"""Check specs/<id>/tasks.json against its spec (see skills/build/references/artifacts.md).

Usage: check_tasks.py SPEC_ID
"""

import json
import re
import sys

from kit_config import project_root

PROJECT_ROOT = project_root()
SPEC_BEHAVIOR_RE = re.compile(r"^- \*\*(\d+\.B\d+) ", re.MULTILINE)
TASK_ID_RE = re.compile(r"[TF]\d+")
COMMIT_SHA_RE = re.compile(r"[0-9a-f]{7,40}")
MAX_PLANNED_TASKS = 8
MAX_TITLE_WORDS = 10


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    spec_dir = PROJECT_ROOT / "specs" / sys.argv[1]
    tasks_path = spec_dir / "tasks.json"
    if not tasks_path.exists():
        print(f"specs/{sys.argv[1]}/tasks.json doesn't exist", file=sys.stderr)
        return 1
    spec_ids = SPEC_BEHAVIOR_RE.findall((spec_dir / "spec.md").read_text())
    problems = task_problems(json.loads(tasks_path.read_text()), spec_dir.name, spec_ids)
    if problems:
        print(f"specs/{sys.argv[1]}/tasks.json: {len(problems)} problem(s)", file=sys.stderr)
        print("\n".join(f"  - {problem}" for problem in problems), file=sys.stderr)
        return 1
    print(f"specs/{sys.argv[1]}/tasks.json: ok")
    return 0


def task_problems(plan: dict, spec_id: str, spec_ids: list[str]) -> list[str]:
    problems = []
    if plan.get("spec") != spec_id:
        problems.append(f"`spec` should be `{spec_id}`")
    if not COMMIT_SHA_RE.fullmatch(str(plan.get("base", ""))):
        problems.append("`base` should be the commit sha before the first task")
    tasks = plan.get("tasks", [])
    if not tasks:
        return [*problems, "`tasks` is empty"]
    for task in tasks:
        problems += single_task_problems(task, spec_ids)
    task_ids = [task.get("id") for task in tasks]
    if len(set(task_ids)) != len(task_ids):
        problems.append("task ids repeat")
    planned_count = sum(1 for task_id in task_ids if str(task_id).startswith("T"))
    if planned_count > MAX_PLANNED_TASKS:
        problems.append(f"{planned_count} planned tasks (max {MAX_PLANNED_TASKS}); split the spec")
    covered_ids = {behavior_id for task in tasks for behavior_id in task.get("covers", [])}
    uncovered = [behavior_id for behavior_id in spec_ids if behavior_id not in covered_ids]
    if uncovered:
        problems.append(f"no task covers {uncovered}")
    return problems


def single_task_problems(task: dict, spec_ids: list[str]) -> list[str]:
    task_id = task.get("id", "?")
    problems = []
    if not TASK_ID_RE.fullmatch(str(task_id)):
        problems.append(f"`{task_id}`: id should be T<n> (planned) or F<n> (fix)")
    title_words = len(str(task.get("title", "")).split())
    if not 0 < title_words <= MAX_TITLE_WORDS:
        problems.append(f"`{task_id}`: title should be 1-{MAX_TITLE_WORDS} words")
    unknown_ids = [
        behavior_id for behavior_id in task.get("covers", []) if behavior_id not in spec_ids
    ]
    if unknown_ids:
        problems.append(f"`{task_id}`: covers {unknown_ids}, which aren't in the spec")
    if not isinstance(task.get("passes"), bool):
        problems.append(f"`{task_id}`: `passes` should be true or false")
    return problems


if __name__ == "__main__":
    sys.exit(main())
