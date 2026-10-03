#!/usr/bin/env python3
"""Lint the product files define-product writes in docs/product/.

Usage:
  lint_product.py [PATH ...]   lint brief.md, market.md, or reviews/product-r<n>.md; with no
                               PATH, every product file in this project; exit 1 on problems
  lint_product.py --hook       SubagentStop hook: lint the market researcher's market.md or the
                               product reviewer's latest review; exit 2 (keep working) on
                               problems, at most 3 times in a row; silent without kit's config

The brief's claims each carry evidence: `sourced` or `inferred` cite market.md's M IDs,
`assumed` and `validated` cite the brief's own PA assumptions, and `stated` is the requester's
word. Once the brief is approved, its PD, PA, and PF IDs keep their meaning, as a spec's do.
"""

import json
import re
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

from kit_config import load_if_set_up, project_root
from lint_outputs import lint_findings
from lint_spec import committed_text, lint_banned_shapes, parse_fields, split_frontmatter

PRODUCT_PATH = Path("docs") / "product"
BRIEF_NAME = "brief.md"
MARKET_NAME = "market.md"
REVIEWS_NAME = "reviews"
RESEARCHER_AGENT = "kit:market-researcher"
REVIEWER_AGENT = "kit:product-reviewer"
MAX_CONSECUTIVE_BLOCKS = 3
SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
FORMAT_GUIDES = {
    RESEARCHER_AGENT: SKILLS_DIR / "research-market" / "references" / "market-format.md",
    REVIEWER_AGENT: SKILLS_DIR / "define-product" / "references" / "brief-format.md",
}

MAX_BRIEF_LINES = 100
MAX_MARKET_LINES = 150
MAX_PITCH_WORDS = 25
MAX_HEAD_WORDS = 20
MAX_TEXT_WORDS = 40
MAX_NOTE_WORDS = 25

STATUSES = ("draft", "approved")
AMBITIONS = ("venture", "bootstrapped", "indie")
VERDICTS = ("pending", "go", "narrow", "pivot", "stop")
BUILDING_VERDICTS = ("go", "narrow")
ASSUMPTION_STATUSES = ("untested", "holds", "fails")
RATINGS = ("strong", "mixed", "weak", "unknown")
DIMENSIONS = ("Pain", "Reach", "Willingness to pay", "Gap", "Edge", "Why you", "Size")
CLAIM_SECTIONS = (
    *("Customer", "Problem", "Alternatives", "Solution", "Why now"),
    *("Market", "Model", "Channels", "Edge", "Why you"),
)
BRIEF_SECTIONS = (
    *CLAIM_SECTIONS,
    *("Decide", "Assumptions", "Verdict", "First version", "Not doing", "Words"),
)
REQUIRED_BRIEF_SECTIONS = (*CLAIM_SECTIONS, "Decide", "Assumptions", "Not doing")
MARKET_SECTIONS = (
    *("Sources", "Competitors", "Alternatives", "Failed attempts"),
    *("Demand", "Complaints", "Unknown"),
)
CITING_SECTIONS = ("Competitors", "Alternatives", "Failed attempts", "Demand", "Complaints")
BULLET_SECTIONS = ("Not doing", "Unknown")


class Rules(NamedTuple):
    limits: dict[str, tuple[int, int]]
    note_labels: dict[str, str]
    id_kinds: dict[str, str]
    none_allowed: frozenset[str]


BRIEF_RULES = Rules(
    limits={
        **dict.fromkeys(CLAIM_SECTIONS, (1, 3)),
        "Decide": (0, 5),
        "Assumptions": (1, 8),
        "Verdict": (len(DIMENSIONS), len(DIMENSIONS)),
        "First version": (1, 8),
        "Not doing": (0, 6),
        "Words": (1, 12),
    },
    note_labels={
        **dict.fromkeys(CLAIM_SECTIONS, "Evidence"),
        "Decide": "Alt",
        "Assumptions": "Test",
    },
    id_kinds={"Decide": "PD", "Assumptions": "PA", "First version": "PF"},
    none_allowed=frozenset(("Decide", "Not doing")),
)
MARKET_RULES = Rules(
    limits={"Sources": (1, 60), **dict.fromkeys(CITING_SECTIONS, (1, 15)), "Unknown": (0, 10)},
    note_labels={},
    id_kinds={"Sources": "M"},
    none_allowed=frozenset((*CITING_SECTIONS[1:], "Unknown")),
)
ID_KINDS = BRIEF_RULES.id_kinds

ITEM_RE = re.compile(r"^- \*\*(?P<head>.+?)\*\*\s*→\s*(?P<text>\S.*)$")
CITATION_RE = re.compile(r"\((?P<cited>M\d+(?:,\s*M\d+)*)\)\s*$")
QUOTE_RE = re.compile(r'"(?P<quote>[^"]+)"|“(?P<curly>[^”]+)”')
USERNAME_RE = re.compile(r"(?<![\w/])u/[A-Za-z0-9_-]{3,}")
MAX_QUOTE_WORDS = 25
NOTE_RE = re.compile(r"^\s+- _(?P<label>[A-Za-z]+):_\s*(?P<text>\S.*)$")
ID_HEAD_RE = re.compile(r"^(?P<item_id>(?P<kind>P[DAF]|M)\d+) (?P<name>\S.*)$")
EVIDENCE_RE = re.compile(r"^(?P<grade>sourced|inferred|assumed|validated|stated)\b(?P<refs>.*)$")
SOURCE_ID_RE = re.compile(r"\bM\d+\b")
ASSUMPTION_ID_RE = re.compile(r"\bPA\d+\b")
BRIEF_ID_RE = re.compile(r"^(?P<kind>P[DAF])(?P<index>\d+)$")
RETIRED_ID_RE = re.compile(r"\bP[DAF]\d+\b")
RATING_RE = re.compile(rf"^(?P<rating>{'|'.join(RATINGS)}): \S")
URL_RE = re.compile(r"https?://\S+")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REVIEW_NAME_RE = re.compile(r"^product-r(?P<round>\d+)\.md$")


class Note(NamedTuple):
    label: str
    text: str


class Item(NamedTuple):
    head: str
    text: str
    notes: tuple[Note, ...]


class Section(NamedTuple):
    name: str
    lines: list[str]
    items: list[Item]
    is_none: bool


class Document(NamedTuple):
    fields: dict[str, str]
    title: str
    intro_lines: list[str]
    sections: dict[str, Section]
    lines: list[str]


def main() -> int:
    if sys.argv[1:] == ["--hook"]:
        return run_hook(json.load(sys.stdin))
    product_paths = [Path(argument) for argument in sys.argv[1:]]
    product_paths = product_paths or find_product_files(project_root())
    if not product_paths:
        print(f"no product files in {PRODUCT_PATH}/; run /kit:define-product", file=sys.stderr)
        return 1
    any_failed = False
    for product_path in product_paths:
        problems = lint(product_path)
        print(format_report(product_path, problems) if problems else f"{product_path}: ok")
        any_failed |= bool(problems)
    return 1 if any_failed else 0


def run_hook(hook_input: dict) -> int:
    agent_type = str(hook_input.get("agent_type") or "")
    config = load_if_set_up() if agent_type in FORMAT_GUIDES else None
    if config is None:
        return 0
    output_path = agent_output_path(agent_type, config.root / PRODUCT_PATH)
    problems = lint(output_path) if output_path.is_file() else ["not written yet"]
    counter_path = Path(tempfile.gettempdir()) / f"kit-product-blocks-{run_id(hook_input)}"
    block_count = int(counter_path.read_text()) + 1 if counter_path.exists() else 1
    if not problems or block_count > MAX_CONSECUTIVE_BLOCKS:
        counter_path.unlink(missing_ok=True)
        return 0
    counter_path.write_text(str(block_count))
    print(format_report(output_path, problems), file=sys.stderr)
    print(f"Fix these before stopping (see {FORMAT_GUIDES[agent_type]}).", file=sys.stderr)
    return 2


def agent_output_path(agent_type: str, product_dir: Path) -> Path:
    if agent_type == RESEARCHER_AGENT:
        return product_dir / MARKET_NAME
    review_rounds = {
        int(name_match.group("round")): path
        for path in (product_dir / REVIEWS_NAME).glob("product-r*.md")
        if (name_match := REVIEW_NAME_RE.match(path.name))
    }
    latest_round = max(review_rounds, default=1)
    return review_rounds.get(latest_round, product_dir / REVIEWS_NAME / "product-r1.md")


def run_id(hook_input: dict) -> str:
    return hook_input.get("agent_id") or hook_input.get("session_id", "unknown")


def find_product_files(root: Path) -> list[Path]:
    product_dir = root / PRODUCT_PATH
    candidates = [
        product_dir / BRIEF_NAME,
        product_dir / MARKET_NAME,
        *sorted((product_dir / REVIEWS_NAME).glob("product-r*.md")),
    ]
    return [path for path in candidates if path.is_file()]


def is_product_file(path: Path, root: Path) -> bool:
    product_dir = (root / PRODUCT_PATH).resolve()
    path = path.resolve()
    is_brief_or_market = path.parent == product_dir and path.name in (BRIEF_NAME, MARKET_NAME)
    is_review = path.parent == product_dir / REVIEWS_NAME and path.name.startswith("product-r")
    return is_brief_or_market or is_review


def lint(product_path: Path) -> list[str]:
    product_path = product_path.resolve()
    text = product_path.read_text()
    if product_path.parent.name == REVIEWS_NAME:
        return lint_review(text, product_path.name)
    if product_path.name == MARKET_NAME:
        return lint_market(text)
    if product_path.name == BRIEF_NAME:
        market_path = product_path.parent / MARKET_NAME
        market_text = market_path.read_text() if market_path.exists() else None
        return lint_brief(text, market_text, committed_text(product_path))
    return [f"not a product file: expected {BRIEF_NAME}, {MARKET_NAME}, or reviews/product-r<n>.md"]


def lint_brief(brief_text: str, market_text: str | None, approved_text: str | None) -> list[str]:
    frontmatter, body = split_frontmatter(brief_text)
    if frontmatter is None:
        return ["frontmatter: missing `---` block with status, ambition, verdict"]
    fields = parse_fields(frontmatter)
    document = parse_document(fields, body)
    problems = [
        *lint_brief_fields(fields),
        *lint_shape(document, BRIEF_SECTIONS, REQUIRED_BRIEF_SECTIONS, MAX_BRIEF_LINES),
        *lint_pitch(document.intro_lines),
        *lint_quotes(document.lines),
    ]
    problems += lint_sections(document, BRIEF_RULES)
    assumptions = {item_id(item): item.text for item in items_in(document, "Assumptions")}
    source_ids = find_source_ids(market_text)
    for claim in items_across(document, CLAIM_SECTIONS):
        problems += lint_evidence(claim, source_ids, assumptions)
    problems += lint_verdict(fields, document)
    problems += lint_features(items_in(document, "First version"), assumptions)
    problems += lint_against_approved(approved_text, id_heads(document), fields)
    return list(dict.fromkeys(problems))


def lint_market(market_text: str) -> list[str]:
    frontmatter, body = split_frontmatter(market_text)
    if frontmatter is None:
        return ["frontmatter: missing `---` block with researched: <date>"]
    fields = parse_fields(frontmatter)
    document = parse_document(fields, body)
    problems = [
        *lint_shape(document, MARKET_SECTIONS, MARKET_SECTIONS, MAX_MARKET_LINES),
        *lint_sections(document, MARKET_RULES),
        *lint_quotes(document.lines),
    ]
    if not DATE_RE.match(fields.get("researched", "")):
        problems.append("frontmatter: `researched:` should be the date, like 2026-10-03")
    if document.title != "Market":
        problems.append("title: first line should be `# Market`")
    if len(document.intro_lines) != 1:
        problems.append("summary: exactly one line under the title, the market in plain words")
    source_ids = find_source_ids(market_text)
    problems += [
        f"{item_id(item)}: a source needs its link after `→`"
        for item in items_in(document, "Sources")
        if not URL_RE.search(item.text)
    ]
    for section_name in CITING_SECTIONS:
        for item in items_in(document, section_name):
            problems += lint_citations(item, source_ids, section_name)
    return list(dict.fromkeys(problems))


def lint_review(review_text: str, file_name: str) -> list[str]:
    frontmatter, body = split_frontmatter(review_text)
    if frontmatter is None:
        return ["frontmatter: missing `---` block with lens, round, verdict"]
    fields = parse_fields(frontmatter)
    problems = []
    if fields.get("lens") != "product":
        problems.append("frontmatter: lens must be `product`")
    if file_name != f"product-r{fields.get('round')}.md" or not REVIEW_NAME_RE.match(file_name):
        problems.append(f"file name: should be `product-r{fields.get('round', '<round>')}.md`")
    if fields.get("verdict") not in ("pass", "fail"):
        problems.append("frontmatter: verdict must be `pass` or `fail`")
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("# "):
        return [*problems, "title: first line should be `# Product review, round <n>`"]
    finding_lines = lines[1:]
    blocker_count = 0
    if [line.strip() for line in finding_lines] != ["none"]:
        finding_problems, blocker_count = lint_findings(finding_lines)
        problems += finding_problems
    expected_verdict = "fail" if blocker_count else "pass"
    if fields.get("verdict") in ("pass", "fail") and fields["verdict"] != expected_verdict:
        problems.append(f"verdict: {blocker_count} blocker(s) means `verdict: {expected_verdict}`")
    return problems


def parse_document(fields: dict[str, str], body: str) -> Document:
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    title = lines[0][2:].strip() if lines and lines[0].startswith("# ") else ""
    intro_lines: list[str] = []
    section_lines: dict[str, list[str]] = {}
    current_lines = intro_lines
    for line in lines[1:] if title else lines:
        if line.startswith("## "):
            current_lines = section_lines.setdefault(line[3:].strip(), [])
        else:
            current_lines.append(line)
    sections = {name: parse_section(name, section) for name, section in section_lines.items()}
    return Document(fields, title, intro_lines, sections, lines)


def parse_section(name: str, lines: list[str]) -> Section:
    is_none = [line.strip() for line in lines] == ["none"]
    items: list[Item] = []
    for line in [] if is_none else lines:
        item_match = ITEM_RE.match(line)
        note_match = NOTE_RE.match(line)
        if item_match:
            items.append(Item(item_match.group("head"), item_match.group("text"), notes=()))
        elif note_match and items:
            note = Note(note_match.group("label"), note_match.group("text"))
            items[-1] = items[-1]._replace(notes=(*items[-1].notes, note))
    return Section(name, lines, items, is_none)


def items_in(document: Document, section_name: str) -> list[Item]:
    section = document.sections.get(section_name)
    return section.items if section else []


def items_across(document: Document, section_names: Iterable[str]) -> list[Item]:
    items: list[Item] = []
    for section_name in section_names:
        items += items_in(document, section_name)
    return items


def id_heads(document: Document) -> dict[str, str]:
    return {
        item_id(item): item.head
        for item in items_across(document, ID_KINDS)
        if ID_HEAD_RE.match(item.head)
    }


def item_id(item: Item) -> str:
    head_match = ID_HEAD_RE.match(item.head)
    return head_match.group("item_id") if head_match else item.head


def lint_brief_fields(fields: dict[str, str]) -> list[str]:
    problems = []
    if fields.get("status") not in STATUSES:
        problems.append(f"frontmatter: status must be one of {list(STATUSES)}")
    if fields.get("ambition") not in AMBITIONS:
        problems.append(f"frontmatter: ambition must be one of {list(AMBITIONS)}")
    if fields.get("verdict") not in VERDICTS:
        problems.append(f"frontmatter: verdict must be one of {list(VERDICTS)}")
    if fields.get("status") == "approved" and fields.get("verdict") == "pending":
        problems.append("frontmatter: an approved brief needs its verdict, not `pending`")
    return problems


def lint_shape(
    document: Document, allowed: tuple[str, ...], required: tuple[str, ...], max_lines: int
) -> list[str]:
    problems = lint_banned_shapes(document.lines)
    if not document.title:
        problems.append("title: first line should be `# <name>`")
    if len(document.lines) > max_lines:
        problems.append(f"body: {len(document.lines)} non-blank lines (max {max_lines})")
    headings = list(document.sections)
    missing = [name for name in required if name not in headings]
    unknown = [name for name in headings if name not in allowed]
    if missing:
        problems.append(f"sections: missing {missing}")
    if unknown:
        problems.append(f"sections: unknown {unknown}; allowed: {list(allowed)}")
    known = [name for name in headings if name in allowed]
    if known != sorted(known, key=allowed.index):
        problems.append(f"sections: order must be {list(allowed)}")
    return problems


def lint_pitch(intro_lines: list[str]) -> list[str]:
    if len(intro_lines) != 1:
        return [f"pitch: {len(intro_lines)} lines under the title; must be one line"]
    pitch_words = len(intro_lines[0].split())
    if pitch_words > MAX_PITCH_WORDS:
        return [f"pitch: {pitch_words} words (max {MAX_PITCH_WORDS})"]
    return []


def lint_sections(document: Document, rules: Rules) -> list[str]:
    problems: list[str] = []
    for section in document.sections.values():
        problems += lint_section(section, rules)
    return problems


def lint_section(section: Section, rules: Rules) -> list[str]:
    if section.name not in rules.limits:
        return []
    if section.is_none:
        return [] if section.name in rules.none_allowed else [f"{section.name}: can't be `none`"]
    if section.name in BULLET_SECTIONS:
        return lint_bullets(section, rules)
    problems = [
        f"{section.name}: `{line.strip()[:50]}` should be `- **<name>** → <text>`"
        for line in section.lines
        if not (ITEM_RE.match(line) or NOTE_RE.match(line))
    ]
    least, most = rules.limits[section.name]
    if not least <= len(section.items) <= most:
        problems.append(f"{section.name}: {len(section.items)} items (allowed {least} to {most})")
    item_ids = [item_id(item) for item in section.items]
    duplicate_ids = sorted({each_id for each_id in item_ids if item_ids.count(each_id) > 1})
    if section.name in rules.id_kinds and duplicate_ids:
        problems.append(f"{section.name}: duplicate IDs {duplicate_ids}")
    for item in section.items:
        problems += lint_item(section.name, item, rules)
    return problems


def lint_bullets(section: Section, rules: Rules) -> list[str]:
    problems = [
        f"{section.name}: `{line.strip()[:50]}` should be a `- ` bullet"
        for line in section.lines
        if not line.startswith("- ")
    ]
    least, most = rules.limits[section.name]
    if not least <= len(section.lines) <= most:
        problems.append(f"{section.name}: {len(section.lines)} items (allowed {least} to {most})")
    return problems


def lint_item(section_name: str, item: Item, rules: Rules) -> list[str]:
    problems = []
    expected_kind = rules.id_kinds.get(section_name)
    head_match = ID_HEAD_RE.match(item.head)
    if expected_kind and not (head_match and head_match.group("kind") == expected_kind):
        problems.append(f"{section_name}: `{item.head[:40]}` should start `{expected_kind}<n> `")
    for part_name, text, limit in (
        ("bold part", item.head, MAX_HEAD_WORDS),
        ("text after →", item.text, MAX_TEXT_WORDS),
        *((note.label, note.text, MAX_NOTE_WORDS) for note in item.notes),
    ):
        if len(text.split()) > limit:
            problems.append(f"{item_id(item)}: {part_name} over {limit} words")
    expected_label = rules.note_labels.get(section_name)
    labels = [note.label for note in item.notes]
    if expected_label and labels != [expected_label]:
        problems.append(f"{item_id(item)}: needs exactly one `- _{expected_label}:_` line")
    elif not expected_label and labels:
        problems.append(f"{item_id(item)}: {section_name} items take no nested lines")
    if section_name == "Assumptions" and item.text not in ASSUMPTION_STATUSES:
        problems.append(f"{item_id(item)}: status must be one of {list(ASSUMPTION_STATUSES)}")
    if section_name == "Verdict" and not RATING_RE.match(item.text):
        problems.append(
            f"Verdict: `{item.head}` should be `<rating>: <why>`, rating {list(RATINGS)}"
        )
    return problems


def find_source_ids(market_text: str | None) -> frozenset[str]:
    if market_text is None:
        return frozenset()
    _, body = split_frontmatter(market_text)
    document = parse_document({}, body)
    return frozenset(item_id(item) for item in items_in(document, "Sources"))


def lint_evidence(item: Item, source_ids: frozenset[str], assumptions: dict[str, str]) -> list[str]:
    evidence = next((note.text for note in item.notes if note.label == "Evidence"), None)
    if evidence is None:
        return []
    evidence_match = EVIDENCE_RE.match(evidence)
    if not evidence_match:
        return [f"{item.head}: evidence starts sourced, inferred, assumed, validated, or stated"]
    grade, refs = evidence_match.group("grade", "refs")
    if grade in ("sourced", "inferred"):
        return lint_source_refs(item.head, grade, refs, source_ids)
    if grade in ("assumed", "validated"):
        return lint_assumption_refs(item.head, grade, refs, assumptions)
    return []


def lint_source_refs(head: str, grade: str, refs: str, source_ids: frozenset[str]) -> list[str]:
    cited_ids = SOURCE_ID_RE.findall(refs)
    if not cited_ids:
        return [f"{head}: `{grade}` cites market.md sources, like `{grade} M2, M5`"]
    unknown_ids = [cited for cited in cited_ids if cited not in source_ids]
    return [f"{head}: {unknown_ids} aren't sources in market.md"] if unknown_ids else []


def lint_assumption_refs(
    head: str, grade: str, refs: str, assumptions: dict[str, str]
) -> list[str]:
    cited_ids = ASSUMPTION_ID_RE.findall(refs)
    if not cited_ids:
        return [f"{head}: `{grade}` cites the assumption, like `{grade} PA2`"]
    problems = [
        f"{head}: {cited} isn't under Assumptions"
        for cited in cited_ids
        if cited not in assumptions
    ]
    if grade == "validated":
        problems += [
            f"{head}: `validated {cited}` needs {cited} to be `holds`"
            for cited in cited_ids
            if assumptions.get(cited, "holds") != "holds"
        ]
    return problems


def lint_citations(item: Item, source_ids: frozenset[str], section_name: str) -> list[str]:
    citation_match = CITATION_RE.search(item.text)
    if not citation_match:
        return [f"{section_name}: `{item.head[:40]}` should end with its sources, like (M2, M5)"]
    cited_ids = SOURCE_ID_RE.findall(citation_match.group("cited"))
    unknown_ids = [cited for cited in cited_ids if cited not in source_ids]
    return [f"{section_name}: {unknown_ids} aren't under Sources"] if unknown_ids else []


def lint_quotes(lines: list[str]) -> list[str]:
    problems = []
    for line in lines:
        for quote_match in QUOTE_RE.finditer(line):
            quote = quote_match.group("quote") or quote_match.group("curly")
            if len(quote.split()) > MAX_QUOTE_WORDS:
                problems.append(f"quote: `{quote[:40]}...` is over {MAX_QUOTE_WORDS} words")
        problems += [
            f"username: `{username}`; quote people without their names"
            for username in USERNAME_RE.findall(line)
        ]
    return problems


def lint_verdict(fields: dict[str, str], document: Document) -> list[str]:
    verdict = fields.get("verdict")
    has_verdict_section = "Verdict" in document.sections
    if verdict == "pending":
        return (
            ["Verdict: leave the section out until the verdict is set"]
            if has_verdict_section
            else []
        )
    problems = [] if has_verdict_section else ["sections: a set verdict needs its Verdict section"]
    ratings = {item.head: item.text.split(":", 1)[0] for item in items_in(document, "Verdict")}
    if has_verdict_section and sorted(ratings) != sorted(DIMENSIONS):
        problems.append(f"Verdict: rate each of {list(DIMENSIONS)} once")
    weak_dimensions = [name for name, rating in ratings.items() if rating == "weak"]
    if verdict == "go" and weak_dimensions:
        problems.append(f"Verdict: `go` with weak {weak_dimensions}; narrow, pivot, or stop")
    if verdict in BUILDING_VERDICTS and "First version" not in document.sections:
        problems.append(f"sections: verdict `{verdict}` needs a First version to build")
    return problems


def lint_features(features: list[Item], assumptions: dict[str, str]) -> list[str]:
    problems = []
    for feature in features:
        cited_ids = ASSUMPTION_ID_RE.findall(feature.text)
        if not cited_ids:
            problems.append(f"{item_id(feature)}: name the assumptions it tests, like `tests PA1`")
        problems += [
            f"{item_id(feature)}: {cited} isn't under Assumptions"
            for cited in cited_ids
            if cited not in assumptions
        ]
    return problems


def lint_against_approved(
    approved_text: str | None, brief_heads: dict[str, str], fields: dict[str, str]
) -> list[str]:
    approved_frontmatter, approved_body = split_frontmatter(approved_text or "")
    approved_fields = parse_fields(approved_frontmatter or "")
    if approved_fields.get("status") != "approved":
        return []
    approved_document = parse_document(approved_fields, approved_body)
    approved_heads = id_heads(approved_document)
    retired_ids = set(RETIRED_ID_RE.findall(fields.get("retired", "")))
    approved_retired = set(RETIRED_ID_RE.findall(approved_fields.get("retired", "")))
    problems = []
    for approved_id, approved_head in sorted(approved_heads.items()):
        if approved_id not in brief_heads and approved_id not in retired_ids:
            problems.append(f"{approved_id}: removed after approval; list it under `retired:`")
        elif approved_id in brief_heads and brief_heads[approved_id] != approved_head:
            problems.append(f"{approved_id}: reworded after approval; retire it and add a new ID")
    if approved_retired - retired_ids:
        problems.append(f"retired: {sorted(approved_retired - retired_ids)} must stay retired")
    reused = sorted(retired_ids & set(brief_heads))
    if reused:
        problems.append(f"retired: {reused} are in use again; retired IDs never come back")
    used_ids = set(approved_heads) | approved_retired
    for new_id in sorted(set(brief_heads) - used_ids):
        problems += lint_new_id(new_id, used_ids)
    return problems


def lint_new_id(new_id: str, used_ids: set[str]) -> list[str]:
    kind, index = id_parts(new_id)
    highest = max(
        (used_index for used_kind, used_index in map(id_parts, used_ids) if used_kind == kind),
        default=0,
    )
    if index <= highest:
        return [f"{new_id}: reuses a number; new {kind} IDs start above {highest}"]
    return []


def id_parts(brief_id: str) -> tuple[str, int]:
    id_match = BRIEF_ID_RE.match(brief_id)
    assert id_match, brief_id
    return id_match.group("kind"), int(id_match.group("index"))


def format_report(product_path: Path, problems: list[str]) -> str:
    problem_lines = "\n".join(f"  - {problem}" for problem in problems)
    return f"{product_path}: {len(problems)} problem(s)\n{problem_lines}"


if __name__ == "__main__":
    sys.exit(main())
