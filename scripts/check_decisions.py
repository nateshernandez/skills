#!/usr/bin/env python3
"""Lint every decision record, so a moved or deleted file a record cites is caught.

Usage: check_decisions.py   (checks docs/decisions/*.md in this repo; exit 1 on problems)
"""

import sys

from kit_config import project_root
from lint_decision import format_report, lint

DECISIONS_DIR = project_root() / "docs" / "decisions"


def main() -> int:
    if sys.argv[1:]:
        print(__doc__, file=sys.stderr)
        return 1
    record_paths = sorted(DECISIONS_DIR.glob("*.md")) if DECISIONS_DIR.exists() else []
    reports = [
        format_report(record_path, problems)
        for record_path in record_paths
        if (problems := lint(record_path))
    ]
    if reports:
        print("\n".join(reports), file=sys.stderr)
        return 1
    print(f"{len(record_paths)} decision record(s): ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
