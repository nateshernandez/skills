#!/usr/bin/env python3
"""Check that a spec's acceptance test file has exactly one test per spec behavior.

Usage: check_coverage.py SPEC_ID   (e.g. 001-track)
The file is `tests.acceptance` in .claude/kit/config.json. Test titles start with the behavior
ID: test("1.B1 Visitor submits a valid email", ...).
"""

import re
import sys

from kit_config import ConfigError, load, relative

SPEC_BEHAVIOR_RE = re.compile(r"^- \*\*(\d+\.B\d+) ", re.MULTILINE)
TEST_TITLE_RE = re.compile(r"\b(?:test|it)\(\s*[\"'`](\d+\.B\d+)\b")
DISABLED_TEST_RE = re.compile(r"\b(?:test|it|describe)\.(skip|fixme|only|fail|todo)\(")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    try:
        config = load()
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    spec_id = sys.argv[1]
    spec_path = config.specs_dir / spec_id / "spec.md"
    test_path = config.acceptance_path(spec_id)
    test_name = relative(test_path, config.root)
    if not test_path.exists():
        print(f"{test_name} doesn't exist; write one test per behavior", file=sys.stderr)
        return 1
    problems = coverage_problems(spec_path.read_text(), test_path.read_text())
    if problems:
        print(f"{test_name}: {len(problems)} problem(s)", file=sys.stderr)
        print("\n".join(f"  - {problem}" for problem in problems), file=sys.stderr)
        return 1
    print(f"{test_name}: one test per behavior")
    return 0


def coverage_problems(spec_text: str, test_text: str) -> list[str]:
    spec_ids = SPEC_BEHAVIOR_RE.findall(spec_text)
    test_ids = TEST_TITLE_RE.findall(test_text)
    problems = []
    missing = [behavior_id for behavior_id in spec_ids if behavior_id not in test_ids]
    extra = sorted(set(test_ids) - set(spec_ids))
    duplicated = sorted(
        {behavior_id for behavior_id in test_ids if test_ids.count(behavior_id) > 1}
    )
    if missing:
        problems.append(f"no test for {missing}")
    if extra:
        problems.append(f"tests for behaviors not in the spec: {extra}")
    if duplicated:
        problems.append(f"more than one test for {duplicated}; one test per behavior")
    disabled = sorted(set(DISABLED_TEST_RE.findall(test_text)))
    if disabled:
        problems.append(f"test.{'/'.join(disabled)} found; acceptance tests all run")
    return problems


if __name__ == "__main__":
    sys.exit(main())
