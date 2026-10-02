#!/usr/bin/env python3
"""Create docs/decisions/<NNNN>-<slug>.md from the template, numbered after the newest record.

Usage: new_decision.py SLUG   (kebab-case, e.g. tenant-isolation)
Prints the new record's path. Numbers only count up, so a record's number is its creation order.
"""

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from kit_config import project_root

DECISIONS_DIR = project_root() / "docs" / "decisions"
TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "write-decision"
    / "assets"
    / "decision-template.md"
)
SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
NUMBERED_FILE_RE = re.compile(r"(\d{4})-")


def main() -> int:
    if len(sys.argv) != 2 or not SLUG_RE.fullmatch(sys.argv[1]):
        print(__doc__, file=sys.stderr)
        return 1
    record_id = f"{next_record_number(DECISIONS_DIR):04d}-{sys.argv[1]}"
    record_path = DECISIONS_DIR / f"{record_id}.md"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now(UTC).date().isoformat()
    record_text = TEMPLATE_PATH.read_text().replace("<id>", record_id).replace("<date>", today)
    record_path.write_text(record_text)
    print(record_path)
    return 0


def next_record_number(decisions_dir: Path) -> int:
    file_names = (
        [path.name for path in decisions_dir.glob("*.md")] if decisions_dir.exists() else []
    )
    used_numbers = [
        int(file_match.group(1))
        for file_match in map(NUMBERED_FILE_RE.match, file_names)
        if file_match
    ]
    return max(used_numbers, default=0) + 1


if __name__ == "__main__":
    sys.exit(main())
