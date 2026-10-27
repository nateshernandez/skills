#!/usr/bin/env python3
"""Lint specs/<id>/design.md against the design format (skills/design-spec/references/).

Usage:
  lint_design.py PATH [PATH ...]   lint files; exit 1 on problems
"""

import re
import sys
from pathlib import Path

from lint_spec import format_report, parse_fields, split_frontmatter

MAX_BODY_LINES = 80
MAX_INVARIANT_WORDS = 20
MAX_SHAPE_WORDS = 25
STATUSES = ("draft", "approved")
SECTION_ORDER = ("Data model", "Interfaces", "Flows", "Invariants")
SHAPE_SECTIONS = ("Data model", "Interfaces", "Flows")
SECTION_HEADING_RE = re.compile(r"^## (.+?)\s*$")
INVARIANT_RE = re.compile(r"^- \*\*(?P<id>\d+\.I\d+) (?P<situation>[^*]+)\*\* → (?P<rule>\S.*)$")
INVARIANT_SHAPE = "`- **1.I1 <situation>** → <rule that always holds>`"
SPEC_NUMBER_RE = re.compile(r"^(\d{3})-")
FENCE_RE = re.compile(r"^```")


def main() -> int:
    if not sys.argv[1:]:
        print(__doc__, file=sys.stderr)
        return 1
    any_failed = False
    for design_path in map(Path, sys.argv[1:]):
        problems = lint(design_path)
        print(format_report(design_path, problems) if problems else f"{design_path}: ok")
        any_failed |= bool(problems)
    return 1 if any_failed else 0


def is_design_file(path: Path, specs_dir: Path) -> bool:
    return path.name == "design.md" and path.resolve().parent.parent == specs_dir.resolve()


def lint(design_path: Path) -> list[str]:
    frontmatter, body = split_frontmatter(design_path.read_text())
    if frontmatter is None:
        return ["frontmatter: missing `---` block with id and status"]
    folder_name = design_path.resolve().parent.name
    fields = parse_fields(frontmatter)
    problems = []
    if fields.get("id") != folder_name:
        problems.append(f"frontmatter: id `{fields.get('id', '')}` doesn't match `{folder_name}`")
    if fields.get("status") not in STATUSES:
        problems.append(f"frontmatter: status must be one of {list(STATUSES)}")
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    if len(lines) > MAX_BODY_LINES:
        problems.append(
            f"body: {len(lines)} non-blank lines (max {MAX_BODY_LINES}); split the spec"
        )
    return problems + lint_lines(lines, spec_number(folder_name))


def spec_number(folder_name: str) -> int:
    number_match = SPEC_NUMBER_RE.match(folder_name)
    return int(number_match.group(1)) if number_match else 0


def lint_lines(lines: list[str], number: int) -> list[str]:
    if not lines or not lines[0].startswith("# Design: "):
        return ["title: first line should be `# Design: <feature name>`"]
    intro_lines, sections = split_sections(lines[1:])
    problems = []
    if len(intro_lines) != 1 or len(intro_lines[0].split()) > MAX_SHAPE_WORDS:
        problems.append(f"intro: one line under the title, ≤ {MAX_SHAPE_WORDS} words: the shape")
    present = list(sections)
    ordered = [name for name in SECTION_ORDER if name in sections]
    if present != ordered:
        problems.append(f"sections: use only {list(SECTION_ORDER)}, in that order")
    if not any(name in sections for name in SHAPE_SECTIONS):
        problems.append("sections: add at least one of Data model, Interfaces, or Flows")
    for name, section_lines in sections.items():
        if not section_lines:
            problems.append(f"{name}: empty; leave the section out")
    problems += lint_flows(sections.get("Flows", []))
    return problems + lint_invariants(sections.get("Invariants"), number)


def split_sections(lines: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    intro_lines: list[str] = []
    sections: dict[str, list[str]] = {}
    current = intro_lines
    in_code_block = False
    for line in lines:
        if FENCE_RE.match(line):
            in_code_block = not in_code_block
        heading = None if in_code_block else SECTION_HEADING_RE.match(line)
        if heading:
            current = sections.setdefault(heading.group(1), [])
        else:
            current.append(line)
    return intro_lines, sections


def lint_flows(flow_lines: list[str]) -> list[str]:
    if flow_lines and not any(line.startswith("```mermaid") for line in flow_lines):
        return ["Flows: draw each flow as a ```mermaid block"]
    return []


def lint_invariants(invariant_lines: list[str] | None, number: int) -> list[str]:
    if invariant_lines is None:
        return ["Invariants: required; each rule that must always hold becomes a unit test"]
    problems = []
    seen_ids: set[str] = set()
    for line in invariant_lines:
        item_match = INVARIANT_RE.match(line)
        if item_match is None:
            problems.append(f"Invariants: `{line[:50]}` should read {INVARIANT_SHAPE}")
            continue
        invariant_id = item_match.group("id")
        if not invariant_id.startswith(f"{number}.I"):
            problems.append(f"Invariants: `{invariant_id}` should start `{number}.I`")
        if invariant_id in seen_ids:
            problems.append(f"Invariants: `{invariant_id}` repeats")
        seen_ids.add(invariant_id)
        if len(item_match.group("rule").split()) > MAX_INVARIANT_WORDS:
            problems.append(f"{invariant_id}: rule is over {MAX_INVARIANT_WORDS} words")
    if not seen_ids and not problems:
        problems.append("Invariants: add at least one")
    return problems


if __name__ == "__main__":
    sys.exit(main())
