#!/usr/bin/env python3
"""Check that a spec's tests cover every behavior and invariant once, at a deliberate level.

Usage: check_coverage.py SPEC_ID   (e.g. 001-track)
Behavior tests live in `tests.acceptance` (end to end) and, when the config has `tests.unit`, in
`tests.unit.acceptance` (unit level). Titles start with the behavior ID:
test("1.B1 Visitor submits a valid email", ...).

Each behavior, and each invariant in design.md (`1.I1`), has exactly one test across both files.
With `tests.unit`, each end-to-end test carries a `// e2e: <why a unit test can't prove it>` line
just above, and a spec may have at most `tests.e2e_per_spec` of them.
"""

import re
import sys
from pathlib import Path
from typing import NamedTuple

from kit_config import Config, ConfigError, load, relative

SPEC_BEHAVIOR_RE = re.compile(r"^- \*\*(\d+\.[BI]\d+) ", re.MULTILINE)
TEST_TITLE_RE = re.compile(r"\b(?:test|it)\(\s*[\"'`](\d+\.[BI]\d+)\b")
DISABLED_TEST_RE = re.compile(r"\b(?:test|it|describe)\.(skip|fixme|only|fail|todo)\(")
E2E_REASON_RE = re.compile(r"^\s*//\s*e2e:\s*\S")
REASON_SEARCH_LINES = 3


class FoundTest(NamedTuple):
    behavior_id: str
    path: Path
    has_reason: bool


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
    test_paths = config.behavior_test_paths(spec_id)
    if not test_paths:
        expected = relative(config.acceptance_path(spec_id), config.root)
        print(f"{expected} doesn't exist; write one test per behavior", file=sys.stderr)
        return 1
    spec_dir = config.specs_dir / spec_id
    design_path = spec_dir / "design.md"
    spec_text = (spec_dir / "spec.md").read_text()
    design_text = design_path.read_text() if design_path.exists() else ""
    tested_ids = SPEC_BEHAVIOR_RE.findall(spec_text + design_text)
    problems = coverage_problems(config, spec_id, tested_ids, test_paths)
    names = ", ".join(relative(path, config.root) for path in test_paths)
    if problems:
        print(f"{names}: {len(problems)} problem(s)", file=sys.stderr)
        print("\n".join(f"  - {problem}" for problem in problems), file=sys.stderr)
        return 1
    print(f"{names}: one test per behavior")
    return 0


def coverage_problems(
    config: Config, spec_id: str, spec_ids: list[str], test_paths: list[Path]
) -> list[str]:
    tests = [found for path in test_paths for found in find_tests(path)]
    test_ids = [found.behavior_id for found in tests]
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
    disabled = sorted(
        {word for path in test_paths for word in DISABLED_TEST_RE.findall(path.read_text())}
    )
    if disabled:
        problems.append(f"test.{'/'.join(disabled)} found; acceptance tests all run")
    return problems + end_to_end_problems(config, spec_id, tests)


def find_tests(path: Path) -> list[FoundTest]:
    text = path.read_text()
    lines = text.splitlines()
    found = []
    for title_match in TEST_TITLE_RE.finditer(text):
        title_line = text.count("\n", 0, title_match.start())
        nearby_lines = lines[max(0, title_line - REASON_SEARCH_LINES) : title_line + 1]
        has_reason = any(E2E_REASON_RE.match(line) for line in nearby_lines)
        found.append(FoundTest(title_match.group(1), path, has_reason))
    return found


def end_to_end_problems(config: Config, spec_id: str, tests: list[FoundTest]) -> list[str]:
    if config.tests.unit is None:
        return []
    end_to_end = [found for found in tests if found.path == config.acceptance_path(spec_id)]
    problems = [
        f"{found.behavior_id} is tested end to end without a reason; add"
        " `// e2e: <why a unit test can't prove it>` above it, or move it to unit level"
        for found in end_to_end
        if not found.has_reason
    ]
    budget = config.tests.e2e_per_spec
    if len(end_to_end) > budget:
        unit_path = relative(config.unit_acceptance_path(spec_id) or config.root, config.root)
        problems.append(
            f"{len(end_to_end)} behaviors are tested end to end (budget {budget}); prove more of"
            f" them in {unit_path}, or ask the requester to raise tests.e2e_per_spec"
        )
    return problems


if __name__ == "__main__":
    sys.exit(main())
