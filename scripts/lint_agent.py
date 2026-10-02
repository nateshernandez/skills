#!/usr/bin/env python3
"""Lint subagent definitions against the agent format (see references/format.md).

Usage:
  lint_agent.py PATH [PATH ...]   lint files; exit 1 on problems
"""

import re
import sys
from pathlib import Path

MAX_DESCRIPTION_CHARS = 200
MAX_BODY_LINES = 8
FOLDED_SCALAR_MARKERS = (">", "|", ">-", "|-")
TOP_LEVEL_FIELD_RE = re.compile(r"^([A-Za-z_-]+):\s*(.*)$")
LIST_ITEM_RE = re.compile(r"^\s+-\s+(\S.*)$")


def main() -> int:
    if not sys.argv[1:]:
        print(__doc__, file=sys.stderr)
        return 1
    any_failed = False
    for agent_path in map(Path, sys.argv[1:]):
        problems = lint(agent_path)
        print(format_report(agent_path, problems) if problems else f"{agent_path}: ok")
        any_failed |= bool(problems)
    return 1 if any_failed else 0


def lint(agent_path: Path) -> list[str]:
    agent_text = agent_path.read_text()
    if not agent_text.startswith("---\n") or "\n---" not in agent_text[4:]:
        return ["frontmatter: missing `---` block"]
    frontmatter_end = agent_text.index("\n---", 4)
    fields, skill_names = parse_frontmatter(agent_text[4:frontmatter_end])
    body = agent_text[frontmatter_end + 4 :].split("\n", 1)[-1]
    # Agents in .claude/agents/ preload skills from .claude/skills/; a plugin's, from its skills/.
    skills_dir = agent_path.resolve().parent.parent / "skills"
    return lint_fields(fields, skill_names, agent_path.stem, skills_dir) + lint_body(body)


def parse_frontmatter(frontmatter: str) -> tuple[dict[str, str], list[str]]:
    fields: dict[str, str] = {}
    skill_names: list[str] = []
    field_name = None
    for line in frontmatter.splitlines():
        field_match = TOP_LEVEL_FIELD_RE.match(line)
        list_item_match = LIST_ITEM_RE.match(line)
        if field_match:
            field_name, field_value = field_match.group(1), field_match.group(2).strip()
            fields[field_name] = "" if field_value in FOLDED_SCALAR_MARKERS else field_value
        elif field_name == "skills" and list_item_match:
            skill_names.append(list_item_match.group(1).strip("\"'"))
        elif field_name == "description" and line.strip():
            fields["description"] = f"{fields['description']} {line.strip()}".strip()
    return fields, skill_names


def lint_fields(
    fields: dict[str, str], skill_names: list[str], file_stem: str, skills_dir: Path
) -> list[str]:
    problems = []
    if fields.get("name") != file_stem:
        problems.append(f"frontmatter: name should be `{file_stem}`, the file name")
    description = fields.get("description", "")
    if "Use when:" not in description or "Not when:" not in description:
        problems.append("description: needs `Use when:` and `Not when:` clauses")
    if len(description) > MAX_DESCRIPTION_CHARS:
        problems.append(f"description: {len(description)} chars (max {MAX_DESCRIPTION_CHARS})")
    if not fields.get("tools"):
        problems.append("frontmatter: list `tools` explicitly; agents get only what they need")
    if not skill_names:
        problems.append("frontmatter: `skills:` needs the skill that holds the procedure")
    if "hooks" in fields:
        problems.append(
            "frontmatter: `hooks:` in agent files never run; use `fence-*` or a settings hook"
        )
    if "fence-deny" in fields and "fence-allow" in fields:
        problems.append("frontmatter: use `fence-deny` or `fence-allow`, not both")
    # A `plugin:skill` name comes from an installed plugin, which this lint can't see.
    missing_skills = [
        name
        for name in skill_names
        if ":" not in name and not (skills_dir / name / "SKILL.md").exists()
    ]
    if missing_skills:
        problems.append(f"skills: {missing_skills} not found in {skills_dir}")
    return problems


def lint_body(body: str) -> list[str]:
    body_lines = [line for line in body.splitlines() if line.strip()]
    problems = []
    if not body_lines:
        problems.append("body: say which skill to run and what to return")
    if len(body_lines) > MAX_BODY_LINES:
        problems.append(
            f"body: {len(body_lines)} non-blank lines (max {MAX_BODY_LINES}); "
            "move the procedure into the skill"
        )
    if any(line.startswith("#") for line in body_lines):
        problems.append("body: no headings; the procedure lives in the skill")
    return problems


def format_report(agent_path: Path, problems: list[str]) -> str:
    problem_lines = "\n".join(f"  - {problem}" for problem in problems)
    return f"{agent_path}: {len(problems)} problem(s)\n{problem_lines}"


if __name__ == "__main__":
    sys.exit(main())
