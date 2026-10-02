#!/usr/bin/env python3
"""Check that every spec item ID a build refers to is still live in its spec.md.

Usage: check_ids.py SPEC_ID   (e.g. 001-track)

IDs look like `1.B4`: spec number, then D (decision) or B (behavior) and an index.
Live files (tasks, tests, probes, plan, report) may cite only active IDs.
History files (progress.md, reviews) may also cite retired ones.
IDs from other specs are allowed everywhere.
"""

import re
import sys
from pathlib import Path
from typing import NamedTuple

from kit_config import Config, ConfigError, load, project_root, relative

ITEM_ID_RE = re.compile(r"(?<![\d.])(\d+)\.([DB])(\d+)\b")
SPEC_ITEM_RE = re.compile(r"^- \*\*(\d+\.[DB]\d+) ", re.MULTILINE)
RETIRED_FIELD_RE = re.compile(r"^retired:\s*(.*)$", re.MULTILINE)


class SpecIds(NamedTuple):
    spec_number: int
    active: frozenset[str]
    retired: frozenset[str]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    try:
        config = load()
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    spec_dir = config.specs_dir / sys.argv[1]
    if not (spec_dir / "spec.md").exists():
        print(f"{spec_dir}/spec.md doesn't exist", file=sys.stderr)
        return 1
    spec_ids = load_spec_ids(spec_dir)
    problems = []
    for path in live_files(spec_dir, config):
        problems += stale_references(path, spec_ids, allow_retired=False)
    for path in history_files(spec_dir):
        problems += stale_references(path, spec_ids, allow_retired=True)
    if problems:
        print(f"{spec_dir.name}: {len(problems)} stale reference(s)", file=sys.stderr)
        print("\n".join(f"  - {problem}" for problem in problems), file=sys.stderr)
        return 1
    print(f"{spec_dir.name}: every ID reference is live")
    return 0


def load_spec_ids(spec_dir: Path) -> SpecIds:
    spec_text = (spec_dir / "spec.md").read_text()
    retired_match = RETIRED_FIELD_RE.search(spec_text.split("\n---", 1)[0])
    retired_text = retired_match.group(1) if retired_match else ""
    return SpecIds(
        spec_number=int(spec_dir.name.split("-", 1)[0]),
        active=frozenset(SPEC_ITEM_RE.findall(spec_text)),
        retired=frozenset(find_ids(retired_text)),
    )


def find_ids(text: str) -> list[str]:
    return [f"{number}.{kind}{index}" for number, kind, index in ITEM_ID_RE.findall(text)]


def live_files(spec_dir: Path, config: Config) -> list[Path]:
    spec_id = spec_dir.name
    candidates = [
        spec_dir / "tasks.json",
        spec_dir / "plan.md",
        spec_dir / "report.md",
        config.acceptance_path(spec_id),
        *config.probe_paths(spec_id),
    ]
    return [path for path in candidates if path.exists()]


def history_files(spec_dir: Path) -> list[Path]:
    candidates = [spec_dir / "progress.md", *sorted((spec_dir / "reviews").glob("*.md"))]
    return [path for path in candidates if path.exists()]


def stale_references(path: Path, spec_ids: SpecIds, *, allow_retired: bool) -> list[str]:
    allowed_ids = spec_ids.active | spec_ids.retired if allow_retired else spec_ids.active
    problems = []
    for item_id in sorted(set(find_ids(path.read_text()))):
        is_this_spec = int(item_id.split(".")[0]) == spec_ids.spec_number
        if not is_this_spec or item_id in allowed_ids:
            continue
        is_retired = item_id in spec_ids.retired
        reason = "is retired; cite its replacement" if is_retired else "isn't in spec.md"
        problems.append(f"{relative(path, project_root())}: `{item_id}` {reason}")
    return problems


if __name__ == "__main__":
    sys.exit(main())
