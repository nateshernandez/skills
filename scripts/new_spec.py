#!/usr/bin/env python3
"""Create specs/<NNN>-<slug>/spec.md from the template, numbered after the newest spec.

Usage: new_spec.py SLUG   (kebab-case, e.g. time-tracker)
Prints the new spec's path. Numbers only count up, so a spec's number is its creation order.
"""

import re
import sys
from pathlib import Path

from kit_config import project_root

SPECS_DIR = project_root() / "specs"
TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1] / "skills" / "write-spec" / "assets" / "spec-template.md"
)
SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
NUMBERED_FOLDER_RE = re.compile(r"(\d{3})-")


def main() -> int:
    if len(sys.argv) != 2 or not SLUG_RE.fullmatch(sys.argv[1]):
        print(__doc__, file=sys.stderr)
        return 1
    spec_number = next_spec_number(SPECS_DIR)
    spec_id = f"{spec_number:03d}-{sys.argv[1]}"
    spec_path = SPECS_DIR / spec_id / "spec.md"
    spec_path.parent.mkdir(parents=True)
    spec_text = TEMPLATE_PATH.read_text().replace("<id>", spec_id).replace("<n>", str(spec_number))
    spec_path.write_text(spec_text)
    print(spec_path)
    return 0


def next_spec_number(specs_dir: Path) -> int:
    folder_names = [path.name for path in specs_dir.glob("*")] if specs_dir.exists() else []
    used_numbers = [
        int(folder_match.group(1))
        for folder_match in map(NUMBERED_FOLDER_RE.match, folder_names)
        if folder_match
    ]
    return max(used_numbers, default=0) + 1


if __name__ == "__main__":
    sys.exit(main())
