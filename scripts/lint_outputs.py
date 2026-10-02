#!/usr/bin/env python3
"""Lint build outputs: review findings, the delivery report, and probes (references/artifacts.md).

Usage:
  lint_outputs.py PATH [PATH ...]   lint specs/<id>/reviews/*.md, specs/<id>/report.md, or
                                    a probe file (`tests.probes` in the config)

A probe's test titles start with `<n>.B<k>` or `<n>.outcome`, and kept probes don't print. A
probe quoted in a review's evidence must be a test title in that spec's probe files.
"""

import re
import sys
from pathlib import Path

from check_ids import load_spec_ids, stale_references
from kit_config import LENSES, Config, ConfigError, load, relative

REPORT_SECTIONS = (
    "Behaviors",
    "Blocked on",
    "Decided without you",
    "Codified",
    "Open notes",
    "Try it",
    "Screens",
)
REQUIRED_REPORT_SECTIONS = ("Behaviors", "Decided without you", "Codified", "Open notes", "Try it")
MAX_FINDINGS = 15
MAX_FINDING_WORDS = 25
MAX_REPORT_LINES = 60

REVIEW_NAME_RE = re.compile(r"^(?P<lens>[a-z]+)-r(?P<round>\d+)\.md$")
FIELD_RE = re.compile(r"^([a-z_]+):\s*(.*)$")
FINDING_RE = re.compile(
    r"^- \*\*\[(?P<severity>blocker|note)\] (?P<ref>[^*]+)\*\* → (?P<text>\S.*)$"
)
FINDING_SHAPE = "`- **[blocker] 1.B2 · file:line** → ...`"
EVIDENCE_RE = re.compile(r"^\s+- _Evidence:_\s*\S")
BEHAVIOR_RESULT_RE = re.compile(r"^- (?P<mark>[✓✗]) \*\*(?P<behavior_id>\d+\.B\d+) [^*]+\*\* → \S")
SPEC_BEHAVIOR_RE = re.compile(r"^- \*\*(\d+\.B\d+) ", re.MULTILINE)
DECISION_RE = re.compile(r"^- \*\*[^*]+\*\* → \S")
BECAUSE_RE = re.compile(r"^\s+- _Because:_\s*\S")
CODIFIED_RE = re.compile(r"^- \*\*`(?P<codified_path>[^`]+)`\*\* → \S")
NOTE_RE = re.compile(r"^- \*\*\[note\] [^*]+\*\* → \S")
IMAGE_RE = re.compile(r"^!\[[^\]]+\]\((?P<image_path>[^)\s]+)\)$")
TEST_TITLE_RE = re.compile(
    r"\b(?:test|it)(?:\.only)?\(\s*(?P<quote>[\"'`])(?P<title>(?:\\.|(?!(?P=quote)).)*)(?P=quote)",
    re.DOTALL,
)
CONSOLE_LOG_RE = re.compile(r"\bconsole\.log\(")
CITED_PROBE_RE = re.compile(r'"(\d+\.(?:B\d+|outcome) [^"]+)"')

Sections = dict[str, list[str]]


def main() -> int:
    if not sys.argv[1:]:
        print(__doc__, file=sys.stderr)
        return 1
    try:
        config = load()
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    any_failed = False
    for output_path in map(Path, sys.argv[1:]):
        problems = lint(output_path, config)
        print(format_report(output_path, problems) if problems else f"{output_path}: ok")
        any_failed |= bool(problems)
    return 1 if any_failed else 0


def is_build_output(path: Path, config: Config) -> bool:
    path = path.resolve()
    is_review = path.parent.name == "reviews" and path.parent.parent.parent == config.specs_dir
    is_report = path.name == "report.md" and path.parent.parent == config.specs_dir
    return is_review or is_report or probe_spec_id(path, config) is not None


def probe_spec_id(path: Path, config: Config) -> str | None:
    template_re = re.escape(config.tests.probes)
    template_re = template_re.replace(re.escape("{spec}"), r"(?P<spec>\d{3}-[a-z0-9-]+?)")
    template_re = template_re.replace(re.escape("{lens}"), "(?:" + "|".join(LENSES) + ")")
    probe_match = re.fullmatch(template_re, relative(path.resolve(), config.root))
    return probe_match.group("spec") if probe_match else None


def lint(output_path: Path, config: Config) -> list[str]:
    output_path = output_path.resolve()
    probe_spec = probe_spec_id(output_path, config)
    if probe_spec is not None:
        return lint_probe(output_path, probe_spec)
    frontmatter, body = split_frontmatter(output_path.read_text())
    if frontmatter is None:
        return ["frontmatter: missing `---` block"]
    fields = parse_fields(frontmatter)
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    if output_path.name == "report.md":
        spec_dir = output_path.parent
        id_problems = stale_references(output_path, load_spec_ids(spec_dir), allow_retired=False)
        return lint_report(fields, lines, spec_dir, config.root) + id_problems
    spec_dir = output_path.parent.parent
    id_problems = stale_references(output_path, load_spec_ids(spec_dir), allow_retired=True)
    cited_problems = lint_cited_probes(lines, config, spec_dir.name)
    return lint_review(fields, lines, output_path.name) + id_problems + cited_problems


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def probe_titles(probe_text: str) -> list[tuple[int, str]]:
    return [
        (line_number(probe_text, title_match.start()), title_match.group("title"))
        for title_match in TEST_TITLE_RE.finditer(probe_text)
    ]


def lint_probe(probe_path: Path, spec_id: str) -> list[str]:
    probe_text = probe_path.read_text()
    spec_number = int(spec_id.split("-", 1)[0])
    title_re = re.compile(rf"^{spec_number}\.(?:B\d+|outcome)\b")
    problems = [
        f"line {title_line}: title `{title[:40]}` should start `{spec_number}.B<k>` (a behavior) "
        f"or `{spec_number}.outcome` (the whole feature)"
        for title_line, title in probe_titles(probe_text)
        if not title_re.match(title)
    ]
    problems += [
        f"line {line_number(probe_text, log_match.start())}: remove `console.log`; "
        "a kept probe asserts, it doesn't print"
        for log_match in CONSOLE_LOG_RE.finditer(probe_text)
    ]
    return problems


def lint_cited_probes(lines: list[str], config: Config, spec_id: str) -> list[str]:
    evidence_text = "\n".join(line for line in lines if EVIDENCE_RE.match(line))
    cited_titles = CITED_PROBE_RE.findall(evidence_text)
    if not cited_titles:
        return []
    probe_paths = config.probe_paths(spec_id)
    known_titles = [title for path in probe_paths for _, title in probe_titles(path.read_text())]
    problems = []
    for cited_title in cited_titles:
        # A citation may end in `...`; what comes before must still be the title's own words.
        title_start = cited_title.removesuffix("...").removesuffix("…").rstrip()
        if not any(title_start in title for title in known_titles):
            problems.append(
                f"evidence: `{title_start[:40]}` isn't a test title in {spec_id}'s probes; "
                "quote the test title exactly"
            )
    return problems


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---\n"):
        return None, text
    frontmatter_end = text.find("\n---", 4)
    if frontmatter_end == -1:
        return None, text
    return text[4:frontmatter_end], text[frontmatter_end + 4 :].split("\n", 1)[-1]


def parse_fields(frontmatter: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in frontmatter.splitlines():
        field_match = FIELD_RE.match(line)
        if field_match:
            fields[field_match.group(1)] = field_match.group(2).strip()
    return fields


def lint_review(fields: dict[str, str], lines: list[str], file_name: str) -> list[str]:
    problems = lint_review_fields(fields, file_name)
    if not lines or not lines[0].startswith("# "):
        return [*problems, "title: first line should be `# <Lens> review, round <n>`"]
    finding_lines = lines[1:]
    if [line.strip() for line in finding_lines] == ["none"]:
        blocker_count = 0
    else:
        findings_problems, blocker_count = lint_findings(finding_lines)
        problems += findings_problems
    expected_verdict = "fail" if blocker_count else "pass"
    if fields.get("verdict") in ("pass", "fail") and fields["verdict"] != expected_verdict:
        problems.append(f"verdict: {blocker_count} blocker(s) means `verdict: {expected_verdict}`")
    return problems


def lint_review_fields(fields: dict[str, str], file_name: str) -> list[str]:
    problems = []
    if fields.get("lens") not in LENSES:
        problems.append(f"frontmatter: lens must be one of {list(LENSES)}")
    if not fields.get("round", "").isdigit():
        problems.append("frontmatter: round must be a number")
    if fields.get("verdict") not in ("pass", "fail"):
        problems.append("frontmatter: verdict must be `pass` or `fail`")
    name_match = REVIEW_NAME_RE.match(file_name)
    expected_name = f"{fields.get('lens')}-r{fields.get('round')}.md"
    if not name_match or file_name != expected_name:
        problems.append(f"file name: should be `{expected_name}`")
    return problems


def lint_findings(finding_lines: list[str]) -> tuple[list[str], int]:
    problems: list[str] = []
    findings: list[list[str]] = []
    for line in finding_lines:
        if line.startswith((" ", "\t")) and findings:
            findings[-1].append(line)
        else:
            findings.append([line])
    blocker_count = 0
    for head, *detail_lines in findings:
        finding_match = FINDING_RE.match(head)
        if not finding_match:
            problems.append(f"findings: `{head[:50]}` should be {FINDING_SHAPE}")
            continue
        blocker_count += finding_match.group("severity") == "blocker"
        if len(finding_match.group("text").split()) > MAX_FINDING_WORDS:
            problems.append(f"findings: `{head[:40]}` is over {MAX_FINDING_WORDS} words")
        evidence_count = sum(1 for line in detail_lines if EVIDENCE_RE.match(line))
        if evidence_count != 1 or len(detail_lines) != 1:
            problems.append(f"findings: `{head[:40]}` needs exactly one `- _Evidence:_` line")
    if len(findings) > MAX_FINDINGS:
        problems.append(f"findings: {len(findings)} (max {MAX_FINDINGS}); keep what matters")
    return problems, blocker_count


def lint_report(
    fields: dict[str, str], lines: list[str], spec_dir: Path, repo_root: Path
) -> list[str]:
    problems = []
    if fields.get("id") != spec_dir.name:
        problems.append(f"frontmatter: id should be `{spec_dir.name}`")
    if fields.get("status") not in ("done", "blocked"):
        problems.append("frontmatter: status must be `done` or `blocked`")
    if len(lines) > MAX_REPORT_LINES:
        problems.append(f"body: {len(lines)} non-blank lines (max {MAX_REPORT_LINES})")
    if not lines or not lines[0].startswith("# "):
        return [*problems, "title: first line should be `# <Feature name>: report`"]
    intro_lines, sections = parse_sections(lines[1:])
    if len(intro_lines) != 1:
        problems.append("outcome: exactly one line under the title")
    problems += lint_report_sections(list(sections))
    problems += lint_blocked_on(sections, fields)
    problems += lint_behavior_results(sections.get("Behaviors", []), spec_dir, fields)
    problems += lint_decisions(sections.get("Decided without you", []))
    problems += lint_codified(sections.get("Codified", []), repo_root)
    problems += lint_open_notes(sections.get("Open notes", []))
    problems += lint_images(sections.get("Screens", []), spec_dir)
    return problems


def parse_sections(lines: list[str]) -> tuple[list[str], Sections]:
    intro_lines: list[str] = []
    sections: Sections = {}
    current_lines = intro_lines
    for line in lines:
        if line.startswith("## "):
            sections[line[3:].strip()] = []
            current_lines = sections[line[3:].strip()]
        else:
            current_lines.append(line)
    return intro_lines, sections


def lint_report_sections(headings: list[str]) -> list[str]:
    problems = []
    missing = [section for section in REQUIRED_REPORT_SECTIONS if section not in headings]
    unknown = [heading for heading in headings if heading not in REPORT_SECTIONS]
    if missing:
        problems.append(f"sections: missing {missing} (see assets/report-template.md)")
    if unknown:
        problems.append(f"sections: unknown {unknown}; allowed: {list(REPORT_SECTIONS)}")
    known = [heading for heading in headings if heading in REPORT_SECTIONS]
    if known != sorted(known, key=REPORT_SECTIONS.index):
        problems.append(f"sections: order must be {list(REPORT_SECTIONS)}")
    return problems


def lint_behavior_results(
    section_lines: list[str], spec_dir: Path, fields: dict[str, str]
) -> list[str]:
    problems = []
    reported: dict[str, str] = {}
    for line in section_lines:
        result_match = BEHAVIOR_RESULT_RE.match(line)
        if result_match:
            reported[result_match.group("behavior_id")] = result_match.group("mark")
        else:
            problems.append(f"Behaviors: `{line[:50]}` should be `- ✓ **1.B1 <situation>** → ...`")
    spec_ids = SPEC_BEHAVIOR_RE.findall((spec_dir / "spec.md").read_text())
    missing = [behavior_id for behavior_id in spec_ids if behavior_id not in reported]
    extra = [behavior_id for behavior_id in reported if behavior_id not in spec_ids]
    if missing:
        problems.append(f"Behaviors: spec behaviors not reported: {missing}")
    if extra:
        problems.append(f"Behaviors: not in the spec: {extra}")
    if fields.get("status") == "done" and "✗" in reported.values():
        problems.append("Behaviors: a ✗ behavior means `status: blocked`, not `done`")
    return problems


def lint_blocked_on(sections: Sections, fields: dict[str, str]) -> list[str]:
    blocked_lines = sections.get("Blocked on", [])
    has_failed_behavior = any(line.startswith("- ✗") for line in sections.get("Behaviors", []))
    problems = [
        f"Blocked on: `{line[:50]}` should be `- **<finding>** → <question>`"
        for line in blocked_lines
        if not DECISION_RE.match(line)
    ]
    if fields.get("status") == "done" and blocked_lines:
        problems.append("Blocked on: a `done` report has nothing blocking; drop the section")
    if fields.get("status") == "blocked" and not (blocked_lines or has_failed_behavior):
        problems.append("status: `blocked` needs a ✗ behavior or a Blocked on item")
    return problems


def lint_decisions(section_lines: list[str]) -> list[str]:
    if [line.strip() for line in section_lines] == ["none"]:
        return []
    problems = []
    for index, line in enumerate(section_lines):
        if DECISION_RE.match(line):
            has_because = index + 1 < len(section_lines) and BECAUSE_RE.match(
                section_lines[index + 1]
            )
            if not has_because:
                problems.append(f"Decided without you: `{line[:40]}` needs a `- _Because:_`")
        elif not BECAUSE_RE.match(line):
            problems.append(f"Decided without you: `{line[:50]}` should be `- **...** → ...`")
    return problems


def lint_codified(section_lines: list[str], repo_root: Path) -> list[str]:
    if [line.strip() for line in section_lines] == ["none"]:
        return []
    problems = []
    for line in section_lines:
        codified_match = CODIFIED_RE.match(line)
        if not codified_match:
            problems.append(f"Codified: `{line[:50]}` should be `` - **`<path>`** → <what> ``")
        elif not (repo_root / codified_match.group("codified_path")).exists():
            problems.append(f"Codified: `{codified_match.group('codified_path')}` doesn't exist")
    return problems


def lint_open_notes(section_lines: list[str]) -> list[str]:
    if [line.strip() for line in section_lines] == ["none"]:
        return []
    return [
        f"Open notes: `{line[:50]}` should be `- **[note] <lens> · <ref>** → ...`"
        for line in section_lines
        if not NOTE_RE.match(line)
    ]


def lint_images(section_lines: list[str], spec_dir: Path) -> list[str]:
    problems = []
    for line in section_lines:
        image_match = IMAGE_RE.match(line.strip())
        if not image_match:
            problems.append(f"Screens: `{line[:50]}` should be `![caption](screens/x.png)`")
        elif not (spec_dir / image_match.group("image_path")).exists():
            problems.append(f"Screens: `{image_match.group('image_path')}` doesn't exist")
    return problems


def format_report(output_path: Path, problems: list[str]) -> str:
    problem_lines = "\n".join(f"  - {problem}" for problem in problems)
    return f"{output_path}: {len(problems)} problem(s)\n{problem_lines}"


if __name__ == "__main__":
    sys.exit(main())
