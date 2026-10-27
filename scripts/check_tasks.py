#!/usr/bin/env python3
"""Check specs/<id>/tasks.json against its spec and design (skills/build/references/artifacts.md).

A task covers behaviors from spec.md and invariants from design.md, when there is one. A plan
whose tasks list `needs` and `files` can build side by side; two tasks that may run together must
write different paths.

Usage: check_tasks.py SPEC_ID
"""

import json
import re
import sys

from kit_config import project_root
from task_graph import conflicting_pairs, is_parallel_plan, parse_tasks

PROJECT_ROOT = project_root()
SPEC_BEHAVIOR_RE = re.compile(r"^- \*\*(\d+\.[BI]\d+) ", re.MULTILINE)
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
    design_path = spec_dir / "design.md"
    design_text = design_path.read_text() if design_path.exists() else ""
    spec_ids = SPEC_BEHAVIOR_RE.findall((spec_dir / "spec.md").read_text() + design_text)
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
    if not problems and is_parallel_plan(tasks):
        problems += parallel_problems(tasks)
    covered_ids = {behavior_id for task in tasks for behavior_id in task.get("covers", [])}
    uncovered = [behavior_id for behavior_id in spec_ids if behavior_id not in covered_ids]
    if uncovered:
        problems.append(f"no task covers {uncovered}")
    return problems


def parallel_problems(tasks: list[dict]) -> list[str]:
    problems = []
    earlier_ids: set[str] = set()
    for task in tasks:
        problems += needs_and_files_problems(task, earlier_ids)
        earlier_ids.add(task["id"])
    if problems:
        return problems
    by_id = {task.task_id: task for task in parse_tasks(tasks)}
    return [
        f"`{first.task_id}` and `{second.task_id}` can run together but both write `{path}`;"
        " give one the other in `needs`, or split the file"
        for first, second, path in conflicting_pairs(list(by_id.values()))
    ]


def needs_and_files_problems(task: dict, earlier_ids: set[str]) -> list[str]:
    task_id = task["id"]
    is_planned = str(task_id).startswith("T")
    problems = []
    needs = task.get("needs")
    if needs is None and is_planned:
        problems.append(f"`{task_id}`: `needs` should list task ids, or [] when it needs none")
    elif needs is not None:
        unknown = [need for need in needs if need not in earlier_ids]
        if unknown:
            problems.append(f"`{task_id}`: needs {unknown}, which aren't earlier tasks")
    files = task.get("files")
    if files is None and is_planned:
        problems.append(f"`{task_id}`: `files` should list what it writes, like `src/a.ts`")
    elif files is not None:
        problems += [
            f"`{task_id}`: file `{entry}` should be a repo-relative path or a folder ending in /"
            for entry in files
            if not valid_file_entry(entry)
        ]
    return problems


def valid_file_entry(entry: object) -> bool:
    if not isinstance(entry, str) or not entry or entry.startswith("/"):
        return False
    return ".." not in entry.split("/") and not any(char in entry for char in "*?[")


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
