#!/usr/bin/env python3
"""Lint Claude Code rule files against the rule format (see references/format.md).

Usage:
  lint_rule.py PATH [PATH ...]   lint files; exit 1 on problems
"""

import re
import sys
from pathlib import Path

MAX_PRINCIPLE_WORDS = 25
MAX_RULES = 8
MAX_BODY_LINES = 40
MAX_PART_WORDS = 20

RULE_RE = re.compile(r"^- \*\*(?P<situation>.+?)\*\*\s*(?:→|->)\s*(?P<action>\S.*)$")
BECAUSE_RE = re.compile(r"^\s+- ([*_])Because:\1\s*(?P<reason>\S.*)$")
EXAMPLE_RE = re.compile(r"^\s+- [✗✓]")
ALWAYS_ON_RE = re.compile(r"^<!--\s*always-on:\s*\S.*-->$")
FILE_NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+\.md")
RULE_SHAPE = "`- **situation** → action`"


def main() -> int:
    if not sys.argv[1:]:
        print(__doc__, file=sys.stderr)
        return 1
    any_failed = False
    for rule_path in map(Path, sys.argv[1:]):
        problems = lint(rule_path)
        print(format_report(rule_path, problems) if problems else f"{rule_path}: ok")
        any_failed |= bool(problems)
    return 1 if any_failed else 0


def lint(rule_path: Path) -> list[str]:
    problems = []
    if not FILE_NAME_RE.fullmatch(rule_path.name):
        problems.append(f"file name: `{rule_path.name}` should be `<scope>-<concern>.md`")
    frontmatter, body = split_frontmatter(rule_path.read_text())
    body_lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    if len(body_lines) > MAX_BODY_LINES:
        problems.append(f"body: {len(body_lines)} non-blank lines (max {MAX_BODY_LINES})")

    always_on = is_always_on(body_lines)
    if always_on:
        body_lines = body_lines[1:]
    if not parse_paths(frontmatter or "") and not always_on:
        problems.append("frontmatter: needs `paths:`, or `<!-- always-on: <reason> -->` under it")

    if not body_lines or not body_lines[0].startswith("# "):
        return [*problems, "title: first line should be `# <Scope> <concern>`"]
    return problems + lint_principle_and_rules(body_lines[1:])


def split_frontmatter(rule_text: str) -> tuple[str | None, str]:
    if not rule_text.startswith("---\n"):
        return None, rule_text
    frontmatter_end = rule_text.find("\n---", 4)
    if frontmatter_end == -1:
        return None, rule_text
    body = rule_text[frontmatter_end + 4 :].split("\n", 1)[-1]
    return rule_text[4:frontmatter_end], body


def is_always_on(body_lines: list[str]) -> bool:
    return bool(body_lines) and bool(ALWAYS_ON_RE.match(body_lines[0].strip()))


def parse_paths(frontmatter: str) -> list[str]:
    globs: list[str] = []
    in_paths = False
    for line in frontmatter.splitlines():
        key_match = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if key_match:
            in_paths = key_match.group(1) == "paths"
            inline_value = key_match.group(2).strip().strip("[]")
            if in_paths and inline_value:
                globs += [glob.strip().strip("\"'") for glob in inline_value.split(",")]
        elif in_paths and line.strip().startswith("- "):
            globs.append(line.strip()[2:].strip().strip("\"'"))
    return [glob for glob in globs if glob]


def lint_principle_and_rules(lines_after_title: list[str]) -> list[str]:
    if not lines_after_title or lines_after_title[0].lstrip().startswith("-"):
        return ["principle: needs one line under the title", *lint_rules(lines_after_title)]
    principle, *rule_lines = lines_after_title
    if word_count(principle) <= MAX_PRINCIPLE_WORDS:
        return lint_rules(rule_lines)
    principle_problem = (
        f"principle: {word_count(principle)} words (max {MAX_PRINCIPLE_WORDS}); "
        "state the one idea, not the explanation"
    )
    return [principle_problem, *lint_rules(rule_lines)]


def word_count(text: str) -> int:
    return len(text.split())


def lint_rules(rule_lines: list[str]) -> list[str]:
    problems = []
    rule_count = 0
    for rule_group in group_rules(rule_lines):
        banned_reason = banned_shape(rule_group[0])
        if banned_reason:
            problems.append(f"rules: {banned_reason}")
            continue
        rule_count += 1
        problems += lint_rule(rule_group)
    if rule_count == 0:
        problems.append(f"rules: needs at least one {RULE_SHAPE} rule")
    if rule_count > MAX_RULES:
        problems.append(f"rules: {rule_count} rules (max {MAX_RULES}); split the file by concern")
    return list(dict.fromkeys(problems))


def group_rules(lines: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    for line in lines:
        if line.startswith((" ", "\t")) and groups:
            groups[-1].append(line)
        else:
            groups.append([line])
    return groups


def banned_shape(line: str) -> str | None:
    if line.startswith("|"):
        return "tables aren't allowed"
    if line.startswith("```"):
        return "code blocks aren't allowed; keep examples to one ✗/✓ line"
    if line.startswith("#"):
        return "only one `#` title; no subsections (one concern per file)"
    if re.match(r"^\d+\.", line):
        return "numbered steps aren't allowed; a procedure is a skill"
    return None


def lint_rule(rule_group: list[str]) -> list[str]:
    head, *detail_lines = rule_group
    head_match = RULE_RE.match(head)
    if not head_match:
        return [f"rules: `{head[:50]}` should be {RULE_SHAPE}"]
    situation = head_match.group("situation")[:40]
    problems = [
        f"rules: {part_name} of `{situation}` is over {MAX_PART_WORDS} words"
        for part_name in ("situation", "action")
        if word_count(head_match.group(part_name)) > MAX_PART_WORDS
    ]

    because_matches = [match for line in detail_lines if (match := BECAUSE_RE.match(line))]
    example_count = sum(1 for line in detail_lines if EXAMPLE_RE.match(line))
    if len(because_matches) != 1:
        problems.append(f"rules: `{situation}` needs exactly one `- _Because:_` line")
    if any(word_count(match.group("reason")) > MAX_PART_WORDS for match in because_matches):
        problems.append(f"rules: Because of `{situation}` is over {MAX_PART_WORDS} words")
    if example_count > 1:
        problems.append(f"rules: `{situation}` has {example_count} examples (max 1)")
    if len(detail_lines) > len(because_matches) + example_count:
        problems.append(f"rules: under `{situation}` only a Because and one ✗/✓ line go")
    return problems


def format_report(rule_path: Path, problems: list[str]) -> str:
    problem_lines = "\n".join(f"  - {problem}" for problem in problems)
    return f"{rule_path}: {len(problems)} problem(s)\n{problem_lines}"


if __name__ == "__main__":
    sys.exit(main())
