#!/usr/bin/env python3
"""Lint a spec.md against the spec format (see references/format.md).

Usage:
  lint_spec.py PATH [PATH ...]   lint files; exit 1 on problems
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

MAX_BODY_LINES = 50
MAX_OUTCOME_WORDS = 25
MAX_PART_WORDS = 20
MAX_DECISIONS = 5
MAX_BEHAVIORS = 12
MAX_NOT_DOING = 6
MAX_IMAGES = 4

STATUSES = ("draft", "approved", "building", "verifying", "done", "blocked")
SIZES = ("S", "M", "L")
SECTION_ORDER = ("Decide", "Behaviors", "Not doing", "Looks like")
REQUIRED_SECTIONS = ("Decide", "Behaviors", "Not doing")
ITEM_SECTIONS = {"Decide": "D", "Behaviors": "B"}
NOTE_LABELS = {"Decide": "Alt", "Behaviors": "Because"}
ITEM_SHAPE = "`- **1.B1 <situation>** → <outcome>`"

ITEM_RE = re.compile(
    r"^- \*\*(?P<item_id>\d+\.[A-Z]\d+) (?P<situation>.+?)\*\*\s*→\s*(?P<outcome>\S.*)$"
)
ITEM_ID_RE = re.compile(r"(\d+)\.([A-Z])(\d+)")
NOTE_RE = re.compile(r"^\s+- _(?P<label>[A-Za-z]+):_\s*(?P<text>\S.*)$")
IMAGE_RE = re.compile(r"^!\[[^\]]+\]\((?P<image_path>[^)\s]+)\)$")
SPEC_ID_RE = re.compile(r"(?P<spec_number>\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*")
FIELD_RE = re.compile(r"^([a-z_]+):\s*(.*)$")


class Note(NamedTuple):
    label: str
    text: str


class Item(NamedTuple):
    item_id: str
    situation: str
    outcome: str
    notes: tuple[Note, ...]


Sections = dict[str, list[str]]


def main() -> int:
    if not sys.argv[1:]:
        print(__doc__, file=sys.stderr)
        return 1
    any_failed = False
    for spec_path in map(Path, sys.argv[1:]):
        problems = lint(spec_path)
        print(format_report(spec_path, problems) if problems else f"{spec_path}: ok")
        any_failed |= bool(problems)
    return 1 if any_failed else 0


def lint(spec_path: Path) -> list[str]:
    spec_path = spec_path.resolve()
    spec_text = spec_path.read_text()
    frontmatter, body = split_frontmatter(spec_text)
    if frontmatter is None:
        return ["frontmatter: missing `---` block with id, status, size"]
    fields = parse_fields(frontmatter)
    folder_match = SPEC_ID_RE.fullmatch(spec_path.parent.name)
    if not folder_match:
        return [f"folder: `{spec_path.parent.name}` should be `<NNN>-<slug>`; use new_spec.py"]
    spec_number = int(folder_match.group("spec_number"))
    items = find_items(spec_text)
    retired_ids = parse_retired(fields)
    return [
        *lint_frontmatter(fields, spec_path.parent.name),
        *lint_body(body, spec_path.parent, spec_number),
        *lint_retired(retired_ids, items, spec_number),
        *lint_against_approved(committed_text(spec_path), items, retired_ids),
    ]


def split_frontmatter(spec_text: str) -> tuple[str | None, str]:
    if not spec_text.startswith("---\n"):
        return None, spec_text
    frontmatter_end = spec_text.find("\n---", 4)
    if frontmatter_end == -1:
        return None, spec_text
    return spec_text[4:frontmatter_end], spec_text[frontmatter_end + 4 :].split("\n", 1)[-1]


def parse_fields(frontmatter: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in frontmatter.splitlines():
        field_match = FIELD_RE.match(line)
        if field_match:
            fields[field_match.group(1)] = field_match.group(2).split("#")[0].strip()
    return fields


def lint_frontmatter(fields: dict[str, str], folder_name: str) -> list[str]:
    problems = []
    spec_id = fields.get("id", "")
    if spec_id != folder_name:
        problems.append(f"frontmatter: id `{spec_id}` doesn't match folder `{folder_name}`")
    if fields.get("status") not in STATUSES:
        problems.append(f"frontmatter: status must be one of {list(STATUSES)}")
    if fields.get("size") not in SIZES:
        problems.append(f"frontmatter: size must be one of {list(SIZES)}")
    return problems


def lint_body(body: str, spec_dir: Path, spec_number: int) -> list[str]:
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    problems = []
    if len(lines) > MAX_BODY_LINES:
        problems.append(
            f"body: {len(lines)} non-blank lines (max {MAX_BODY_LINES}); split into two specs"
        )
    problems += lint_banned_shapes(lines)
    if not lines or not lines[0].startswith("# "):
        return [*problems, "title: first line should be `# <Feature name>`"]
    intro_lines, sections, unknown_headings = parse_sections(lines[1:])
    problems += lint_outcome(intro_lines)
    problems += lint_section_headings(list(sections), unknown_headings)
    for section_name, prefix in ITEM_SECTIONS.items():
        id_prefix = f"{spec_number}.{prefix}"
        problems += lint_items(section_name, id_prefix, sections.get(section_name, []))
    problems += lint_not_doing(sections.get("Not doing", []))
    problems += lint_images(sections.get("Looks like", []), spec_dir)
    return list(dict.fromkeys(problems))


def lint_banned_shapes(lines: list[str]) -> list[str]:
    problems = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            problems.append("body: tables aren't allowed; use item bullets")
        elif stripped.startswith(("```", "~~~")):
            problems.append("body: code blocks aren't allowed; a spec says what, not how")
        elif stripped.startswith("### "):
            problems.append("body: no `###` subsections; split the spec instead")
    return problems


def parse_sections(lines: list[str]) -> tuple[list[str], Sections, list[str]]:
    intro_lines: list[str] = []
    sections: Sections = {}
    unknown_headings: list[str] = []
    current_lines = intro_lines
    for line in lines:
        if line.startswith("## "):
            heading = line[3:].strip()
            if heading not in SECTION_ORDER:
                unknown_headings.append(heading)
            sections[heading] = []
            current_lines = sections[heading]
        else:
            current_lines.append(line)
    return intro_lines, sections, unknown_headings


def lint_outcome(intro_lines: list[str]) -> list[str]:
    if len(intro_lines) != 1:
        return [f"outcome: {len(intro_lines)} lines under the title; must be one line"]
    outcome_words = len(intro_lines[0].split())
    if outcome_words > MAX_OUTCOME_WORDS:
        return [f"outcome: {outcome_words} words (max {MAX_OUTCOME_WORDS})"]
    return []


def lint_section_headings(headings: list[str], unknown_headings: list[str]) -> list[str]:
    problems = []
    missing = [section for section in REQUIRED_SECTIONS if section not in headings]
    if missing:
        problems.append(f"sections: missing {missing} (see assets/spec-template.md)")
    if unknown_headings:
        problems.append(f"sections: unknown {unknown_headings}; allowed: {list(SECTION_ORDER)}")
    known_headings = [heading for heading in headings if heading in SECTION_ORDER]
    if known_headings != sorted(known_headings, key=SECTION_ORDER.index):
        problems.append(f"sections: order must be {list(SECTION_ORDER)}")
    return problems


def lint_items(section_name: str, id_prefix: str, section_lines: list[str]) -> list[str]:
    if section_name == "Decide" and [line.strip() for line in section_lines] == ["none"]:
        return []
    items, problems = parse_items(section_name, section_lines)
    is_decision = section_name == "Decide"
    limit = MAX_DECISIONS if is_decision else MAX_BEHAVIORS
    if not is_decision and not items:
        problems.append(f"{section_name}: needs at least one {ITEM_SHAPE} item")
    if len(items) > limit:
        problems.append(f"{section_name}: {len(items)} items (max {limit}); split the spec")
    item_ids = [item.item_id for item in items]
    duplicate_ids = sorted({item_id for item_id in item_ids if item_ids.count(item_id) > 1})
    if duplicate_ids:
        problems.append(f"{section_name}: duplicate ids {duplicate_ids}")
    for item in items:
        problems += lint_item(section_name, id_prefix, item)
    return problems


def parse_items(section_name: str, section_lines: list[str]) -> tuple[list[Item], list[str]]:
    items: list[Item] = []
    problems: list[str] = []
    for line in section_lines:
        item_match = ITEM_RE.match(line)
        note_match = NOTE_RE.match(line)
        if item_match:
            items.append(Item(*item_match.group("item_id", "situation", "outcome"), notes=()))
        elif note_match and items:
            note = Note(*note_match.group("label", "text"))
            items[-1] = items[-1]._replace(notes=(*items[-1].notes, note))
        else:
            problems.append(f"{section_name}: `{line.strip()[:50]}` should be {ITEM_SHAPE}")
    return items, problems


def lint_item(section_name: str, id_prefix: str, item: Item) -> list[str]:
    problems = []
    if not re.fullmatch(rf"{re.escape(id_prefix)}\d+", item.item_id):
        problems.append(f"{section_name}: `{item.item_id}` should look like `{id_prefix}<index>`")
    for part_name, text in (("situation", item.situation), ("outcome", item.outcome)):
        if len(text.split()) > MAX_PART_WORDS:
            problems.append(f"{item.item_id}: {part_name} over {MAX_PART_WORDS} words")
    allowed_label = NOTE_LABELS[section_name]
    if any(note.label != allowed_label for note in item.notes) or len(item.notes) > 1:
        problems.append(f"{item.item_id}: only one nested `- _{allowed_label}:_` line allowed")
    if any(len(note.text.split()) > MAX_PART_WORDS for note in item.notes):
        problems.append(f"{item.item_id}: {allowed_label} over {MAX_PART_WORDS} words")
    if section_name == "Decide" and not item.notes:
        problems.append(f"{item.item_id}: a decision needs one `- _Alt:_` line, else it's a fact")
    return problems


def lint_not_doing(section_lines: list[str]) -> list[str]:
    if [line.strip() for line in section_lines] == ["none"]:
        return []
    problems = [
        f"Not doing: `{line.strip()[:50]}` should be a `- ` bullet"
        for line in section_lines
        if not line.startswith("- ")
    ]
    if len(section_lines) > MAX_NOT_DOING:
        problems.append(f"Not doing: {len(section_lines)} items (max {MAX_NOT_DOING})")
    problems += [
        f"Not doing: `{line[2:40]}` is over {MAX_PART_WORDS} words"
        for line in section_lines
        if len(line.split()) - 1 > MAX_PART_WORDS
    ]
    return problems


def lint_images(section_lines: list[str], spec_dir: Path) -> list[str]:
    problems = []
    for line in section_lines:
        image_match = IMAGE_RE.match(line.strip())
        if not image_match:
            problems.append(f"Looks like: `{line.strip()[:50]}` should be `![caption](path)`")
        elif not (spec_dir / image_match.group("image_path")).exists():
            problems.append(f"Looks like: `{image_match.group('image_path')}` doesn't exist")
    if len(section_lines) > MAX_IMAGES:
        problems.append(f"Looks like: {len(section_lines)} images (max {MAX_IMAGES})")
    return problems


def find_items(spec_text: str) -> list[Item]:
    return [
        Item(*item_match.group("item_id", "situation", "outcome"), notes=())
        for item_match in map(ITEM_RE.match, spec_text.splitlines())
        if item_match
    ]


def parse_retired(fields: dict[str, str]) -> frozenset[str]:
    retired_text = fields.get("retired", "")
    return frozenset(item_id_match.group(0) for item_id_match in ITEM_ID_RE.finditer(retired_text))


def lint_retired(retired_ids: frozenset[str], items: list[Item], spec_number: int) -> list[str]:
    problems = [
        f"retired: `{item_id}` belongs to spec {item_id.split('.')[0]}, not {spec_number}"
        for item_id in sorted(retired_ids)
        if int(item_id.split(".")[0]) != spec_number
    ]
    reused_ids = sorted(retired_ids & {item.item_id for item in items})
    if reused_ids:
        problems.append(f"retired: {reused_ids} are still in use; retired IDs never come back")
    return problems


def committed_text(spec_path: Path) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(spec_path.parent), "show", f"HEAD:./{spec_path.name}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout if completed.returncode == 0 else None


def lint_against_approved(
    approved_text: str | None, items: list[Item], retired_ids: frozenset[str]
) -> list[str]:
    approved_frontmatter, _ = split_frontmatter(approved_text or "")
    approved_fields = parse_fields(approved_frontmatter or "")
    if approved_fields.get("status", "draft") == "draft":
        return []
    assert approved_text is not None
    approved_items = {item.item_id: item for item in find_items(approved_text)}
    approved_retired = parse_retired(approved_fields)
    current_items = {item.item_id: item for item in items}
    problems = []
    for item_id, approved_item in approved_items.items():
        current_item = current_items.get(item_id)
        if current_item is None and item_id not in retired_ids:
            problems.append(f"{item_id}: removed after approval; list it under `retired:`")
        elif current_item is not None and wording(current_item) != wording(approved_item):
            problems.append(f"{item_id}: reworded after approval; retire it and add a new ID")
    if approved_retired - retired_ids:
        problems.append(f"retired: {sorted(approved_retired - retired_ids)} must stay retired")
    used_ids = set(approved_items) | approved_retired
    for item_id in sorted(set(current_items) - used_ids):
        kind, index = kind_and_index(item_id)
        used_parts = map(kind_and_index, used_ids)
        highest = max((used for used_kind, used in used_parts if used_kind == kind), default=0)
        if index <= highest:
            problems.append(f"{item_id}: reuses a number; new {kind} IDs start above {highest}")
    return problems


def wording(item: Item) -> tuple[str, str]:
    return item.situation, item.outcome


def kind_and_index(item_id: str) -> tuple[str, int]:
    item_id_match = ITEM_ID_RE.fullmatch(item_id)
    assert item_id_match, item_id
    return item_id_match.group(2), int(item_id_match.group(3))


def format_report(spec_path: Path, problems: list[str]) -> str:
    problem_lines = "\n".join(f"  - {problem}" for problem in problems)
    return f"{spec_path}: {len(problems)} problem(s)\n{problem_lines}"


if __name__ == "__main__":
    sys.exit(main())
