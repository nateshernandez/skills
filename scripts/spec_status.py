#!/usr/bin/env python3
"""Show where a build stands, read from its files in specs/<id>/.

Usage:
  spec_status.py            one line per spec, in number order: id, status, tasks done
  spec_status.py SPEC       detail for one spec (`001-track` or just `1`): next task,
                            latest review verdicts, report
"""

import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

from kit_config import project_root

SPECS_DIR = project_root() / "specs"
STATUS_RE = re.compile(r"^status:\s*(\S+)", re.MULTILINE)
VERDICT_RE = re.compile(r"^verdict:\s*(\S+)", re.MULTILINE)
REVIEW_NAME_RE = re.compile(r"^(?P<lens>[a-z]+)-r(?P<round>\d+)\.md$")


class Task(NamedTuple):
    task_id: str
    title: str
    passes: bool


class Review(NamedTuple):
    lens: str
    round_number: int
    verdict: str


def main() -> int:
    if len(sys.argv) > 2:
        print(__doc__, file=sys.stderr)
        return 1
    if len(sys.argv) == 1:
        spec_dirs = sorted(path.parent for path in SPECS_DIR.glob("*/spec.md"))
        for spec_dir in spec_dirs:
            print(summary_line(spec_dir))
        if not spec_dirs:
            print(f"no specs in {SPECS_DIR}")
        return 0
    spec_dir = resolve_spec_dir(sys.argv[1])
    if not (spec_dir / "spec.md").exists():
        print(f"{spec_dir}/spec.md doesn't exist; run /kit:write-spec first", file=sys.stderr)
        return 1
    print(detail(spec_dir))
    return 0


def resolve_spec_dir(spec_arg: str) -> Path:
    if not spec_arg.isdigit():
        return SPECS_DIR / spec_arg
    numbered_dirs = sorted(SPECS_DIR.glob(f"{int(spec_arg):03d}-*"))
    return numbered_dirs[0] if numbered_dirs else SPECS_DIR / spec_arg


def summary_line(spec_dir: Path) -> str:
    tasks = load_tasks(spec_dir)
    done_count = sum(task.passes for task in tasks)
    return f"{spec_dir.name}: {spec_status(spec_dir)}, tasks {done_count}/{len(tasks)}"


def detail(spec_dir: Path) -> str:
    tasks = load_tasks(spec_dir)
    next_task = next((task for task in tasks if not task.passes), None)
    lines = [summary_line(spec_dir)]
    lines.append(
        f"next task: {next_task.task_id} {next_task.title}" if next_task else "next task: none"
    )
    reviews = latest_reviews(spec_dir)
    if reviews:
        lines.append(f"review round {reviews[0].round_number}:")
        lines += [f"  {review.lens}: {review.verdict}" for review in reviews]
    else:
        lines.append("reviews: none yet")
    lines.append("report: written" if (spec_dir / "report.md").exists() else "report: not yet")
    return "\n".join(lines)


def spec_status(spec_dir: Path) -> str:
    status_match = STATUS_RE.search((spec_dir / "spec.md").read_text())
    return status_match.group(1) if status_match else "unknown"


def load_tasks(spec_dir: Path) -> list[Task]:
    tasks_path = spec_dir / "tasks.json"
    if not tasks_path.exists():
        return []
    raw_tasks = json.loads(tasks_path.read_text())["tasks"]
    return [Task(task["id"], task["title"], task["passes"]) for task in raw_tasks]


def latest_reviews(spec_dir: Path) -> list[Review]:
    reviews = []
    for review_path in (spec_dir / "reviews").glob("*.md"):
        name_match = REVIEW_NAME_RE.match(review_path.name)
        verdict_match = VERDICT_RE.search(review_path.read_text())
        if name_match and verdict_match:
            round_number = int(name_match.group("round"))
            reviews.append(Review(name_match.group("lens"), round_number, verdict_match.group(1)))
    if not reviews:
        return []
    latest_round = max(review.round_number for review in reviews)
    return sorted(review for review in reviews if review.round_number == latest_round)


if __name__ == "__main__":
    sys.exit(main())
