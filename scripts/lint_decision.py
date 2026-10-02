#!/usr/bin/env python3
"""Lint a decision record against the format (see references/format.md).

Usage:
  lint_decision.py PATH [PATH ...]   lint records; exit 1 on problems
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

MAX_BODY_LINES = 40
MAX_BULLET_WORDS = 25
KINDS = ("technical", "policy")
STATUSES = ("accepted", "superseded")
SECTION_LIMITS = {
    "Decision": 6,
    "Why": 5,
    "Alternatives": 4,
    "Consequences": 6,
    "Enforced by": 6,
}
REQUIRED_SECTIONS = ("Decision", "Why", "Alternatives", "Consequences")
MUTABLE_FIELDS = frozenset(("code", "status", "superseded_by"))
MAIN_REFS = ("origin/main", "main")

RECORD_NAME_RE = re.compile(r"\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*")
FIELD_RE = re.compile(r"^([a-z_]+):\s*(.*)$")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
GLOB_CHARS_RE = re.compile(r"[*?\[\]]")
ALTERNATIVE_RE = re.compile(r"^- \*\*[^*]+\*\* → \S")
ENFORCER_RE = re.compile(r"^- `(?P<enforcer_path>[^`]+)` → \S")


class Record(NamedTuple):
    fields: dict[str, str]
    title: str
    context_lines: list[str]
    sections: dict[str, list[str]]
    body_lines: list[str]


def main() -> int:
    if not sys.argv[1:]:
        print(__doc__, file=sys.stderr)
        return 1
    any_failed = False
    for record_path in map(Path, sys.argv[1:]):
        problems = lint(record_path)
        print(format_report(record_path, problems) if problems else f"{record_path}: ok")
        any_failed |= bool(problems)
    return 1 if any_failed else 0


def is_decision_record(path: Path) -> bool:
    is_in_decisions = path.parent.name == "decisions" and path.parent.parent.name == "docs"
    return is_in_decisions and path.suffix == ".md"


def lint(record_path: Path) -> list[str]:
    record_path = record_path.resolve()
    if not RECORD_NAME_RE.fullmatch(record_path.stem):
        return [
            f"file name: `{record_path.name}` should be `<NNNN>-<slug>.md`; use new_decision.py"
        ]
    record = parse_record(record_path.read_text())
    if record is None:
        return ["frontmatter: missing `---` block (see assets/decision-template.md)"]
    repo_root = record_path.parents[2]
    return [
        *lint_frontmatter(record.fields, record_path.stem, repo_root),
        *lint_body(record, repo_root),
        *lint_against_main(record, record_path, repo_root),
    ]


def parse_record(record_text: str) -> Record | None:
    if not record_text.startswith("---\n"):
        return None
    frontmatter_end = record_text.find("\n---", 4)
    if frontmatter_end == -1:
        return None
    fields = parse_fields(record_text[4:frontmatter_end])
    body = record_text[frontmatter_end + 4 :].split("\n", 1)[-1]
    body_lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    title = body_lines[0] if body_lines else ""
    context_lines: list[str] = []
    sections: dict[str, list[str]] = {}
    current_lines = context_lines
    for line in body_lines[1:]:
        if line.startswith("## "):
            current_lines = sections.setdefault(line[3:].strip(), [])
        else:
            current_lines.append(line)
    return Record(fields, title, context_lines, sections, body_lines)


def parse_fields(frontmatter: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in frontmatter.splitlines():
        field_match = FIELD_RE.match(line)
        if field_match:
            fields[field_match.group(1)] = field_match.group(2).split("#")[0].strip()
    return fields


def parse_code_paths(fields: dict[str, str]) -> list[str]:
    return [path.strip() for path in fields.get("code", "").split(",") if path.strip()]


def lint_frontmatter(fields: dict[str, str], record_id: str, repo_root: Path) -> list[str]:
    problems = []
    if fields.get("id") != record_id:
        problems.append(f"frontmatter: id `{fields.get('id')}` doesn't match file `{record_id}`")
    if fields.get("kind") not in KINDS:
        problems.append(f"frontmatter: kind must be one of {list(KINDS)}")
    if not DATE_RE.fullmatch(fields.get("date", "")):
        problems.append("frontmatter: date must be `YYYY-MM-DD`")
    spec_id = fields.get("spec", "")
    if spec_id != "none" and not (repo_root / "specs" / spec_id / "spec.md").exists():
        problems.append(f"frontmatter: spec `{spec_id}` has no specs/<id>/spec.md; or use `none`")
    return [
        *problems,
        *lint_code_paths(fields, repo_root),
        *lint_status(fields, record_id, repo_root),
    ]


def lint_code_paths(fields: dict[str, str], repo_root: Path) -> list[str]:
    code_paths = parse_code_paths(fields)
    if fields.get("kind") == "technical" and not code_paths:
        return ["code: a technical record cites the code that implements it; none means wait"]
    problems = []
    for code_path in code_paths:
        if GLOB_CHARS_RE.search(code_path):
            problems.append(f"code: `{code_path}` is a glob; cite files or directories")
        elif not (repo_root / code_path).exists():
            problems.append(f"code: `{code_path}` doesn't exist; update it if the code moved")
    return problems


def lint_status(fields: dict[str, str], record_id: str, repo_root: Path) -> list[str]:
    status = fields.get("status")
    if status not in STATUSES:
        return [f"frontmatter: status must be one of {list(STATUSES)}"]
    successor_id = fields.get("superseded_by", "")
    if status == "accepted":
        return ["frontmatter: only a superseded record has superseded_by"] if successor_id else []
    if not successor_id or successor_id == record_id:
        return ["frontmatter: a superseded record names its replacement in superseded_by"]
    if not (repo_root / "docs" / "decisions" / f"{successor_id}.md").exists():
        return [f"frontmatter: superseded_by `{successor_id}` has no docs/decisions/<id>.md"]
    return []


def lint_body(record: Record, repo_root: Path) -> list[str]:
    problems = []
    if len(record.body_lines) > MAX_BODY_LINES:
        problems.append(f"body: {len(record.body_lines)} non-blank lines (max {MAX_BODY_LINES})")
    problems += lint_banned_shapes(record.body_lines)
    if not record.title.startswith("# "):
        return [*problems, "title: first line should be `# <the decision as a fact>`"]
    if len(record.context_lines) != 1:
        problems.append(f"context: {len(record.context_lines)} lines under the title; must be one")
    problems += lint_section_headings(list(record.sections))
    for section_name, section_lines in record.sections.items():
        problems += lint_bullets(section_name, section_lines)
    problems += [
        f"Alternatives: `{line[:50]}` should be `- **<option>** → <why not>`"
        for line in record.sections.get("Alternatives", [])
        if not ALTERNATIVE_RE.match(line)
    ]
    problems += lint_enforcers(record.sections.get("Enforced by", []), repo_root)
    return list(dict.fromkeys(problems))


def lint_banned_shapes(lines: list[str]) -> list[str]:
    problems = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            problems.append("body: tables aren't allowed; use bullets")
        elif stripped.startswith(("```", "~~~")):
            problems.append("body: code blocks aren't allowed; code says how, the record says why")
        elif stripped.startswith("### "):
            problems.append("body: no `###` subsections; one decision per record")
    return problems


def lint_section_headings(headings: list[str]) -> list[str]:
    problems = []
    missing = [section for section in REQUIRED_SECTIONS if section not in headings]
    if missing:
        problems.append(f"sections: missing {missing} (see assets/decision-template.md)")
    unknown = [heading for heading in headings if heading not in SECTION_LIMITS]
    if unknown:
        problems.append(f"sections: unknown {unknown}; allowed: {list(SECTION_LIMITS)}")
    known = [heading for heading in headings if heading in SECTION_LIMITS]
    if known != sorted(known, key=list(SECTION_LIMITS).index):
        problems.append(f"sections: order must be {list(SECTION_LIMITS)}")
    return problems


def lint_bullets(section_name: str, section_lines: list[str]) -> list[str]:
    problems = [
        f"{section_name}: `{line.strip()[:50]}` should be a top-level `- ` bullet"
        for line in section_lines
        if not line.startswith("- ")
    ]
    problems += [
        f"{section_name}: `{line[2:40]}` is over {MAX_BULLET_WORDS} words"
        for line in section_lines
        if len(line.split()) - 1 > MAX_BULLET_WORDS
    ]
    limit = SECTION_LIMITS.get(section_name)
    if not section_lines:
        problems.append(f"{section_name}: needs at least one bullet")
    elif limit is not None and len(section_lines) > limit:
        problems.append(f"{section_name}: {len(section_lines)} bullets (max {limit})")
    return problems


def lint_enforcers(section_lines: list[str], repo_root: Path) -> list[str]:
    problems = []
    for line in section_lines:
        enforcer_match = ENFORCER_RE.match(line)
        if not enforcer_match:
            problems.append(
                f"Enforced by: `{line[:50]}` should be `` - `<path>` → <what it checks> ``"
            )
        elif not (repo_root / enforcer_match.group("enforcer_path")).exists():
            problems.append(f"Enforced by: `{enforcer_match.group('enforcer_path')}` doesn't exist")
    return problems


def lint_against_main(record: Record, record_path: Path, repo_root: Path) -> list[str]:
    main_text = text_on_main(record_path, repo_root)
    main_record = parse_record(main_text) if main_text else None
    if main_record is None:
        return []
    problems = [
        f"frontmatter: `{field_name}` is frozen once on main; supersede the record instead"
        for field_name in set(main_record.fields) | set(record.fields)
        if field_name not in MUTABLE_FIELDS
        and main_record.fields.get(field_name) != record.fields.get(field_name)
    ]
    if main_record.body_lines != record.body_lines:
        problems.append("body: frozen once on main; write a new record that supersedes this one")
    if main_record.fields.get("status") == "superseded" and succession(record) != succession(
        main_record
    ):
        problems.append("frontmatter: a superseded record stays superseded by the same record")
    return problems


def succession(record: Record) -> tuple[str | None, str | None]:
    return record.fields.get("status"), record.fields.get("superseded_by")


def text_on_main(record_path: Path, repo_root: Path) -> str | None:
    relative_path = record_path.relative_to(repo_root).as_posix()
    for ref in MAIN_REFS:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{ref}:{relative_path}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            return completed.stdout
    return None


def format_report(record_path: Path, problems: list[str]) -> str:
    problem_lines = "\n".join(f"  - {problem}" for problem in problems)
    return f"{record_path}: {len(problems)} problem(s)\n{problem_lines}"


if __name__ == "__main__":
    sys.exit(main())
