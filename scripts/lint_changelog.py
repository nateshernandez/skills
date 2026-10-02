#!/usr/bin/env python3
"""Lint the harness CHANGELOG against references/format.md.

Usage:
  lint_changelog.py [PATH]   lint PATH (default: .claude/CHANGELOG.md); exit 1 on problems
"""

import re
import sys
from itertools import pairwise
from pathlib import Path
from typing import Literal, NamedTuple

from kit_config import project_root

CHANGELOG_PATH = project_root() / ".claude" / "CHANGELOG.md"
TITLE = "# Harness changelog"
KINDS = ["Added", "Changed", "Removed", "Fixed"]
MAX_HEADLINE_WORDS = 15
MAX_WHY_WORDS = 25
# Stems of words that sound like information but carry none; `\w*` catches the inflections.
VAGUE_STEMS = [
    "improv", "enhanc", "streamlin", "robust", "comprehensive", "seamless", "leverag",
    "various", "ensur", "better", "utiliz", "optimiz", "updat", "modif", "tweak",
]  # fmt: skip

DATE_HEADING_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})$")
ENTRY_RE = re.compile(rf"^- \*\*(?:{'|'.join(KINDS)})\*\* `[^`]+`(?:, `[^`]+`)*: (\S.*)$")
WHY_RE = re.compile(r"^  - _Why:_ (\S.*)$")
VAGUE_WORD_RE = re.compile(rf"\b(?:{'|'.join(VAGUE_STEMS)})\w*", re.IGNORECASE)

LineKind = Literal["date", "entry", "why", "other"]


class Line(NamedTuple):
    number: int
    text: str


def main() -> int:
    arguments = sys.argv[1:]
    if len(arguments) > 1 or (arguments and not Path(arguments[0]).is_file()):
        print(__doc__, file=sys.stderr)
        return 1
    changelog_path = Path(arguments[0]) if arguments else CHANGELOG_PATH
    problems = lint(changelog_path.read_text())
    print(format_report(changelog_path, problems) if problems else f"{changelog_path}: ok")
    return 1 if problems else 0


def lint(changelog_text: str) -> list[str]:
    lines = [
        Line(number, text.rstrip())
        for number, text in enumerate(changelog_text.splitlines(), start=1)
        if text.strip()
    ]
    if not lines or lines[0].text != TITLE:
        return [f"line 1: must be `{TITLE}`"]
    body_lines = lines[2:]  # skip the title and the principle line
    return lint_dates(body_lines) + lint_entries(body_lines)


def lint_dates(body_lines: list[Line]) -> list[str]:
    problems = []
    if body_lines and classify(body_lines[0].text) != "date":
        problems.append(f"line {body_lines[0].number}: entries must sit under a `## YYYY-MM-DD`")
    date_lines = [line for line in body_lines if classify(line.text) == "date"]
    for newer, older in pairwise(date_lines):
        if older.text >= newer.text:
            problems.append(
                f"line {older.number}: `{older.text}` must be older than `{newer.text}`; "
                "newest first, one heading per day"
            )
    return problems


def lint_entries(body_lines: list[Line]) -> list[str]:
    kinds = [classify(line.text) for line in body_lines]
    previous_kinds = [None, *kinds[:-1]]
    next_kinds = [*kinds[1:], None]
    problems = []
    for line, kind, previous_kind, next_kind in zip(
        body_lines, kinds, previous_kinds, next_kinds, strict=True
    ):
        if kind == "other":
            problems.append(
                f"line {line.number}: `{line.text[:50]}` isn't a date heading, "
                f"`- **<{'|'.join(KINDS)}>** `<path>`: <what>`, or `  - _Why:_`"
            )
        if kind == "entry" and next_kind != "why":
            problems.append(f"line {line.number}: entry needs exactly one `  - _Why:_` under it")
        if kind == "why" and previous_kind != "entry":
            problems.append(f"line {line.number}: `_Why:_` must sit directly under an entry")
        problems += lint_wording(line)
    return problems


def classify(text: str) -> LineKind:
    if DATE_HEADING_RE.match(text):
        return "date"
    if ENTRY_RE.match(text):
        return "entry"
    if WHY_RE.match(text):
        return "why"
    return "other"


def lint_wording(line: Line) -> list[str]:
    if entry_match := ENTRY_RE.match(line.text):
        label, wording, max_words = "headline", entry_match.group(1), MAX_HEADLINE_WORDS
    elif why_match := WHY_RE.match(line.text):
        label, wording, max_words = "Why", why_match.group(1), MAX_WHY_WORDS
    else:
        return []
    problems = []
    word_count = len(wording.split())
    if word_count > max_words:
        problems.append(
            f"line {line.number}: {label} is {word_count} words (max {max_words}); "
            "keep the one fact that matters"
        )
    vague_words = sorted({match.group(0).lower() for match in VAGUE_WORD_RE.finditer(wording)})
    if vague_words:
        problems.append(
            f"line {line.number}: vague {vague_words}; name the specific behavior or cause"
        )
    return problems


def format_report(changelog_path: Path, problems: list[str]) -> str:
    problem_lines = "\n".join(f"  - {problem}" for problem in problems)
    return f"{changelog_path}: {len(problems)} problem(s)\n{problem_lines}"


if __name__ == "__main__":
    sys.exit(main())
