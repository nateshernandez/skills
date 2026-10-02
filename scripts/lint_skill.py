#!/usr/bin/env python3
"""Lint SKILL.md files against the skill format (see references/format.md).

Usage:
  lint_skill.py PATH [PATH ...]   lint files; exit 1 on problems
"""

import re
import sys
from pathlib import Path

MAX_DESCRIPTION_CHARS = 200
MAX_BODY_LINES = 60
MAX_NEVER_ITEMS = 5
MAX_FLOW_NODES = 10
MAX_LINE_WORDS = 20

REQUIRED_SECTIONS = ["Goal", "In", "Out", "Flow", "Rules", "Done When", "Never"]
ALL_SECTIONS = [*REQUIRED_SECTIONS, "More"]
BULLET_SECTIONS = ["In", "Out", "Done When", "Never", "More"]
SECTION_BY_LOWERCASE = {section.lower(): section for section in ALL_SECTIONS}
HOW_TO_WORDS = ["then", "first", "make sure", "step", "must", "always", "you should", "follow"]
FOLDED_SCALAR_MARKERS = (">", "|", ">-", "|-")

REQUESTER_PHRASE_RE = re.compile(
    r"\b(?:the\s+)?(?:user|users|human|someone)\s+(?:asks?|wants?|requests?|says?)\b"
    r"|\bwhen asked\b",
    re.IGNORECASE,
)
SECTION_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
FILE_REFERENCE_RE = re.compile(r"[\w./-]+\.(?:md|py|sh|js|ts|json|ya?ml|txt)\b")
MERMAID_LABEL_RE = re.compile(r'"[^"]*"')
MERMAID_NODE_RE = re.compile(r"\b([A-Za-z_]\w*)\s*[\[\(\{]")
RULE_RE = re.compile(r"^- \*\*.+?\*\*\s*(?:→|->)\s*\S")
BECAUSE_RE = re.compile(r"^\s+- ([*_])Because:\1\s*\S")
RULE_SHAPE = "`- **When** → do`"

Sections = dict[str, list[str]]


def main() -> int:
    if not sys.argv[1:]:
        print(__doc__, file=sys.stderr)
        return 1
    any_failed = False
    for skill_path in map(Path, sys.argv[1:]):
        problems = lint(skill_path)
        print(format_report(skill_path, problems) if problems else f"{skill_path}: ok")
        any_failed |= bool(problems)
    return 1 if any_failed else 0


def lint(skill_path: Path) -> list[str]:
    frontmatter, body = split_frontmatter(skill_path.read_text())
    if frontmatter is None:
        return ["frontmatter: missing `---` block with name and description"]
    frontmatter_problems = lint_frontmatter(parse_frontmatter(frontmatter), skill_path.parent)
    return frontmatter_problems + lint_body(body, skill_path.parent)


def split_frontmatter(skill_text: str) -> tuple[str | None, str]:
    if not skill_text.startswith("---\n"):
        return None, skill_text
    frontmatter_end = skill_text.find("\n---", 4)
    if frontmatter_end == -1:
        return None, skill_text
    body = skill_text[frontmatter_end + 4 :].split("\n", 1)[-1].lstrip("\n")
    return skill_text[4:frontmatter_end], body


def parse_frontmatter(frontmatter: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    field_name = None
    for line in frontmatter.splitlines():
        field_match = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if field_match and not line.startswith((" ", "\t")):
            field_name, field_value = field_match.group(1), field_match.group(2).strip()
            is_folded = field_value in FOLDED_SCALAR_MARKERS
            fields[field_name] = "" if is_folded else field_value.strip("\"'")
        elif field_name and line.strip():
            fields[field_name] = (fields[field_name] + " " + line.strip()).strip()
    return fields


def lint_frontmatter(fields: dict[str, str], skill_dir: Path) -> list[str]:
    return lint_name(fields.get("name", ""), skill_dir) + lint_description(
        fields.get("description", "")
    )


def lint_name(name: str, skill_dir: Path) -> list[str]:
    if not name:
        return ["frontmatter: missing `name`"]
    if name != skill_dir.name:
        return [f"frontmatter: name `{name}` doesn't match folder `{skill_dir.name}`"]
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        return [f"frontmatter: name `{name}` should be kebab-case"]
    return []


def lint_description(description: str) -> list[str]:
    if not description:
        return ["frontmatter: missing `description`"]
    problems = []
    if "Use when:" not in description:
        problems.append("description: needs a `Use when:` clause")
    if "Not when:" not in description:
        problems.append("description: needs a `Not when:` clause naming the nearest neighbor")
    if len(description) > MAX_DESCRIPTION_CHARS:
        problems.append(
            f"description: {len(description)} chars (max {MAX_DESCRIPTION_CHARS}); "
            "it routes, it doesn't explain"
        )
    how_to_words_found = [
        word
        for word in HOW_TO_WORDS
        if re.search(rf"\b{re.escape(word)}\b", description, re.IGNORECASE)
    ]
    if how_to_words_found:
        problems.append(
            f"description: how-to words {how_to_words_found}; move instructions into the body"
        )
    requester_phrase = REQUESTER_PHRASE_RE.search(description)
    if requester_phrase:
        problems.append(
            f"description: `{requester_phrase.group(0)}` names who asks; "
            "describe the task situation, since agents route here too"
        )
    return problems


def lint_body(body: str, skill_dir: Path) -> list[str]:
    problems = []
    body_line_count = sum(1 for line in body.splitlines() if line.strip())
    if body_line_count > MAX_BODY_LINES:
        problems.append(
            f"body: {body_line_count} non-blank lines (max {MAX_BODY_LINES}); "
            "move depth to references/ or split the skill"
        )
    sections, unknown_headings = parse_sections(body)
    problems += lint_section_headings(sections, unknown_headings)
    problems += lint_prose(body)
    problems += lint_section_contents(sections)
    problems += lint_more_references(sections.get("More", []), skill_dir)
    return problems


def parse_sections(body: str) -> tuple[Sections, list[str]]:
    sections: Sections = {}
    unknown_headings: list[str] = []
    current_section = None
    for line in body.splitlines():
        heading_match = SECTION_HEADING_RE.match(line)
        if heading_match:
            heading = heading_match.group(1)
            current_section = SECTION_BY_LOWERCASE.get(heading.lower())
            if current_section:
                sections[current_section] = []
            else:
                unknown_headings.append(heading)
        elif current_section and line.strip():
            sections[current_section].append(line.rstrip())
    return sections, unknown_headings


def lint_section_headings(sections: Sections, unknown_headings: list[str]) -> list[str]:
    problems = []
    missing_sections = [section for section in REQUIRED_SECTIONS if section not in sections]
    if missing_sections:
        problems.append(f"body: missing `## ` sections {missing_sections} (see assets/template.md)")
    if unknown_headings:
        problems.append(f"body: unknown sections {unknown_headings}; allowed: {ALL_SECTIONS}")
    return problems


def lint_prose(body: str) -> list[str]:
    problems = []
    in_code_block = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_code_block = not in_code_block
            continue
        if in_code_block or stripped.startswith("#"):
            continue
        if stripped.startswith("|"):
            problems.append(f"body: tables aren't allowed; use {RULE_SHAPE} bullets")
            continue
        # A rule's situation and action are read separately, so measure each side of the arrow.
        segments = re.split(r"→|->", stripped.lstrip("-* "))
        word_count = max(len(segment.split()) for segment in segments)
        if word_count > MAX_LINE_WORDS:
            problems.append(
                f"body: line reads like prose ({word_count} words): `{stripped[:60]}...`"
            )
    return list(dict.fromkeys(problems))


def lint_section_contents(sections: Sections) -> list[str]:
    problems = []
    goal_lines = sections.get("Goal")
    if goal_lines is not None and len(goal_lines) != 1:
        problems.append(f"Goal: {len(goal_lines)} lines; must be one line")
    if "Flow" in sections:
        problems += lint_flow(sections["Flow"])
    if "Rules" in sections:
        problems += lint_rules(sections["Rules"])
    for section in BULLET_SECTIONS:
        if section in sections:
            problems += lint_bullet_section(section, sections[section])
    return problems


def lint_flow(flow_lines: list[str]) -> list[str]:
    flow_lines = [line.strip() for line in flow_lines]
    if not flow_lines or flow_lines[0] != "```mermaid" or "```" not in flow_lines[1:]:
        return ["Flow: must be a single ```mermaid block"]
    closing_fence = flow_lines.index("```", 1)
    diagram_lines = flow_lines[1:closing_fence]
    problems = []
    if flow_lines[closing_fence + 1 :]:
        problems.append("Flow: text outside the mermaid block; put it in a node or a rule")
    if not diagram_lines or not diagram_lines[0].startswith(("flowchart", "graph")):
        return [*problems, "Flow: mermaid block must start with `flowchart TD`"]
    node_ids: set[str] = set()
    for line in diagram_lines[1:]:
        node_ids |= set(MERMAID_NODE_RE.findall(MERMAID_LABEL_RE.sub('""', line)))
    if len(node_ids) > MAX_FLOW_NODES:
        problems.append(f"Flow: {len(node_ids)} nodes (max {MAX_FLOW_NODES}); split the skill")
    return problems


def lint_rules(rule_lines: list[str]) -> list[str]:
    if [line.strip() for line in rule_lines] == ["none"]:
        return []
    if not rule_lines:
        return ["Rules: needs at least one rule (or `none`)"]
    problems = []
    rule_awaiting_because = None
    for line in rule_lines:
        excerpt = line.strip()[:50]
        if BECAUSE_RE.match(line):
            if rule_awaiting_because is None:
                problems.append(f"Rules: `{excerpt}` isn't under a rule")
            rule_awaiting_because = None
            continue
        if rule_awaiting_because is not None:
            problems.append(f"Rules: `{rule_awaiting_because}` has no `- *Because:*` line")
            rule_awaiting_because = None
        if RULE_RE.match(line):
            rule_awaiting_because = excerpt
        elif not line.strip().startswith("|"):  # lint_prose already reports tables
            problems.append(
                f"Rules: `{excerpt}` should be {RULE_SHAPE} or an indented `- *Because:*`"
            )
    if rule_awaiting_because is not None:
        problems.append(f"Rules: `{rule_awaiting_because}` has no `- *Because:*` line")
    return problems


def lint_bullet_section(section: str, section_lines: list[str]) -> list[str]:
    section_lines = [line.strip() for line in section_lines]
    if section in ("Never", "More") and section_lines == ["none"]:
        return []
    problems = []
    stray_lines = [line for line in section_lines if not is_bullet(line)]
    if stray_lines:
        problems.append(f"{section}: `{stray_lines[0][:60]}` should be a bullet")
    bullet_count = len(section_lines) - len(stray_lines)
    if bullet_count == 0 and section != "More":
        problems.append(f"{section}: needs at least one bullet")
    if section == "Done When" and not all(line.startswith("- [ ]") for line in section_lines):
        problems.append("Done When: every item should be a `- [ ]` checkbox")
    if section == "Never" and bullet_count > MAX_NEVER_ITEMS:
        problems.append(
            f"Never: {bullet_count} items (max {MAX_NEVER_ITEMS}); "
            "the skill is probably doing too much"
        )
    return problems


def is_bullet(line: str) -> bool:
    return line.startswith(("- ", "* "))


def lint_more_references(more_lines: list[str], skill_dir: Path) -> list[str]:
    file_references = sorted(set(FILE_REFERENCE_RE.findall(" ".join(more_lines))))
    return [
        f"More: `{file_reference}` doesn't exist"
        for file_reference in file_references
        if not (skill_dir / file_reference).exists()
    ]


def format_report(skill_path: Path, problems: list[str]) -> str:
    problem_lines = "\n".join(f"  - {problem}" for problem in problems)
    return f"{skill_path}: {len(problems)} problem(s)\n{problem_lines}"


if __name__ == "__main__":
    sys.exit(main())
