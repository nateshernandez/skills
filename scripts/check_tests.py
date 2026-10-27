#!/usr/bin/env python3
"""Check that test files share their helpers instead of copying them.

Usage:
  check_tests.py [FILE ...]   check these test files, or every spec's tests when none given

Needs `tests.support` in the config: the folder where helpers shared by test files live. A
top-level helper of 4 or more lines that is declared in two test files, or under another name
with the same body, or that a support file already declares, fails. Move it to the support
folder and import it. Prints one line per problem; exit 1 on a problem.
"""

import hashlib
import re
import sys
from pathlib import Path
from typing import NamedTuple

from kit_config import Config, ConfigError, load, relative, test_glob

MIN_HELPER_LINES = 4
SUPPORT_SUFFIXES = (".ts", ".tsx", ".js", ".mjs")
HELPER_START_RE = re.compile(
    r"^(?:export )?(?:async )?"
    r"(?:function\s+(?P<function>\w+)|const\s+(?P<arrow>\w+)\s*=\s*(?:async\s*)?\()"
)
HELPER_END_RE = re.compile(r"^[})\]]+;?$")


class Helper(NamedTuple):
    name: str
    path: Path
    body_hash: str


def main() -> int:
    try:
        config = load()
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    if config.tests.support is None:
        print("no `tests.support` in the config; nothing to check")
        return 0
    paths = [Path(argument).resolve() for argument in sys.argv[1:]] or spec_test_paths(config)
    problems = check_paths(paths, config)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"test helpers: none repeated across {len(paths)} test file(s)")
    return 0


def spec_test_paths(config: Config) -> list[Path]:
    templates = [config.tests.acceptance, config.tests.probes]
    if config.tests.unit:
        templates.append(config.tests.unit.acceptance)
    return sorted(
        {path for template in templates for path in config.root.glob(test_glob(template))}
    )


def check_paths(paths: list[Path], config: Config) -> list[str]:
    """Problems for `paths`, each compared with every spec's tests and the support folder."""
    support_dir = config.tests.support
    assert support_dir is not None
    support_helpers = [
        helper
        for support_path in sorted(support_dir.rglob("*"))
        if support_path.suffix in SUPPORT_SUFFIXES
        for helper in find_helpers(support_path)
    ]
    all_helpers = [
        helper for test_path in spec_test_paths(config) for helper in find_helpers(test_path)
    ]
    checked = {path.resolve() for path in paths}
    problems = []
    for helper in all_helpers:
        if helper.path.resolve() not in checked:
            continue
        problems += helper_problems(helper, all_helpers, support_helpers, config)
    return sorted(set(problems))


def helper_problems(
    helper: Helper, all_helpers: list[Helper], support_helpers: list[Helper], config: Config
) -> list[str]:
    support_name = relative(config.tests.support or config.root, config.root)
    problems = []
    in_support = [other for other in support_helpers if helper_is_same(helper, other)]
    if in_support:
        problems.append(
            f"`{helper.name}` in {relative(helper.path, config.root)} is already in"
            f" {relative(in_support[0].path, config.root)}; delete the copy and import it"
        )
    copies = [other for other in all_helpers if helper_is_same(helper, other)]
    places = sorted({relative(copy.path, config.root) for copy in copies})
    if len(places) > 1:
        problems.append(
            f"`{helper.name}` is declared in {', '.join(places)}; move one copy to"
            f" {support_name}/ and import it from there"
        )
    return problems


def helper_is_same(first: Helper, second: Helper) -> bool:
    return first.name == second.name or first.body_hash == second.body_hash


def find_helpers(path: Path) -> list[Helper]:
    lines = path.read_text().splitlines()
    helpers = []
    for start, line in enumerate(lines):
        start_match = HELPER_START_RE.match(line)
        if start_match is None:
            continue
        end = next((i for i in range(start + 1, len(lines)) if HELPER_END_RE.match(lines[i])), None)
        if end is None or end - start + 1 < MIN_HELPER_LINES:
            continue
        name = start_match.group("function") or start_match.group("arrow")
        helpers.append(Helper(name, path, body_hash(lines[start + 1 : end])))
    return helpers


def body_hash(body_lines: list[str]) -> str:
    squashed = "\n".join(line.strip() for line in body_lines if line.strip())
    return hashlib.sha1(squashed.encode()).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
