"""Order the tasks in specs/<id>/tasks.json: which are ready, which can run together.

Imported by check_tasks.py, spec_status.py, mark_task.py, and land_task.py; not run on its own.

A planned task may list `needs` (task ids that must pass first) and `files` (the paths it will
write: a file, or a folder ending in `/`). A task with neither follows the one before it in the
list, so a plain list stays a sequential plan. A task's colocated tests, `x.test.ts` for `x.ts`,
belong to it without being listed.
"""

from itertools import combinations
from pathlib import PurePosixPath
from typing import NamedTuple

TEST_MARKERS = ("test", "spec")


class GraphTask(NamedTuple):
    task_id: str
    needs: tuple[str, ...]
    files: tuple[str, ...]
    passes: bool


def parse_tasks(raw_tasks: list[dict]) -> list[GraphTask]:
    """Each task with its needs filled in: unlisted means the task before it in the list."""
    tasks = []
    for position, raw_task in enumerate(raw_tasks):
        previous_ids = (raw_tasks[position - 1]["id"],) if position else ()
        needs = raw_task.get("needs")
        tasks.append(
            GraphTask(
                task_id=raw_task["id"],
                needs=tuple(needs) if needs is not None else previous_ids,
                files=tuple(raw_task.get("files", ())),
                passes=raw_task["passes"],
            )
        )
    return tasks


def is_parallel_plan(raw_tasks: list[dict]) -> bool:
    return any("needs" in raw_task or "files" in raw_task for raw_task in raw_tasks)


def ready_tasks(tasks: list[GraphTask]) -> list[GraphTask]:
    passing_ids = {task.task_id for task in tasks if task.passes}
    return [
        task
        for task in tasks
        if not task.passes and all(need in passing_ids for need in task.needs)
    ]


def can_run_together(tasks: list[GraphTask], first: GraphTask, second: GraphTask) -> bool:
    return not (reaches(tasks, first, second) or reaches(tasks, second, first))


def reaches(tasks: list[GraphTask], start: GraphTask, goal: GraphTask) -> bool:
    """Whether `start` needs `goal`, directly or through other tasks."""
    by_id = {task.task_id: task for task in tasks}
    pending = list(start.needs)
    seen: set[str] = set()
    while pending:
        task_id = pending.pop()
        if task_id == goal.task_id:
            return True
        if task_id in seen or task_id not in by_id:
            continue
        seen.add(task_id)
        pending += by_id[task_id].needs
    return False


def conflicting_pairs(tasks: list[GraphTask]) -> list[tuple[GraphTask, GraphTask, str]]:
    """Tasks that may run together yet write the same path, with the path."""
    conflicts = []
    for first, second in combinations(tasks, 2):
        if not can_run_together(tasks, first, second):
            continue
        shared = next(
            (
                first_entry
                for first_entry in first.files
                for second_entry in second.files
                if entries_overlap(first_entry, second_entry)
            ),
            None,
        )
        if shared:
            conflicts.append((first, second, shared))
    return conflicts


def entries_overlap(first: str, second: str) -> bool:
    return covers_path(first, second) or covers_path(second, first)


def covers_path(entry: str, path: str) -> bool:
    if entry.endswith("/"):
        return path.startswith(entry)
    return path == entry or path in colocated_tests(entry)


def colocated_tests(source: str) -> set[str]:
    source_path = PurePosixPath(source)
    return {
        str(source_path.with_name(f"{source_path.stem}.{marker}{source_path.suffix}"))
        for marker in TEST_MARKERS
    }


def stray_paths(changed_paths: list[str], task: GraphTask) -> list[str]:
    """Changed paths the task never declared; specs/ holds build state and is never stray."""
    return [
        path
        for path in changed_paths
        if not path.startswith("specs/") and not any(covers_path(e, path) for e in task.files)
    ]
