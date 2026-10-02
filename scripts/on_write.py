#!/usr/bin/env python3
"""PostToolUse hook: check each file Claude writes and report problems in the same turn.

Usage: on_write.py   (reads the hook JSON on stdin; registered in hooks/hooks.json)

Does nothing in a project without .claude/kit/config.json. Otherwise, by what was written:
  specs/<id>/spec.md                            lint_spec.py
  specs/<id>/reviews/*.md, report.md, a probe   lint_outputs.py
  docs/decisions/*.md                           lint_decision.py
  .claude/skills/*/SKILL.md                     lint_skill.py
  .claude/rules/*.md                            lint_rule.py
  .claude/agents/*.md                           lint_agent.py
  .claude/CHANGELOG.md                          lint_changelog.py, check_branch_dates.py
  a file matching `format` or `lint`            the config's format, then lint, command
  a .css file, when the config has `design`     check_tokens.py
  any file, when the config has `architecture`  check_shape.py
Exit 2 sends the problems back to Claude; any other outcome stays silent.
"""

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import check_branch_dates
import check_shape
import check_tokens
import lint_agent
import lint_changelog
import lint_decision
import lint_outputs
import lint_rule
import lint_skill
import lint_spec
from kit_config import Config, ConfigError, OnWrite, fill, load_if_set_up, relative

Linter = Callable[[Path, Config], list[str]]

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
FORMAT_GUIDES = {
    "spec": "skills/write-spec/references/format.md",
    "outputs": "skills/build/references/artifacts.md",
    "decision": "skills/write-decision/references/format.md",
    "skill": "skills/write-skill/references/format.md",
    "rule": "skills/write-rule/references/format.md",
    "agent": "skills/write-agent/references/format.md",
    "changelog": "skills/write-changelog-entry/references/format.md",
}


def main() -> int:
    if sys.argv[1:]:
        print(__doc__, file=sys.stderr)
        return 1
    hook_input = json.load(sys.stdin)
    try:
        config = load_if_set_up()
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 2
    written_path = Path(hook_input.get("tool_input", {}).get("file_path", "")).resolve()
    if config is None or not written_path.is_file() or not written_path.is_relative_to(config.root):
        return 0
    report = (
        format_and_lint(written_path, config)
        or check_kit_file(written_path, config)
        or check_css(written_path, config)
        or check_code_shape(written_path, config)
    )
    if not report:
        return 0
    print(report, file=sys.stderr)
    return 2


def check_kit_file(path: Path, config: Config) -> str | None:
    kind = next((kind for kind, matches in kit_file_kinds(path, config).items() if matches), None)
    if kind is None:
        return None
    problems = LINTERS[kind](path, config)
    if not problems:
        return None
    problem_lines = "\n".join(f"  - {problem}" for problem in problems)
    heading = f"{relative(path, config.root)}: {len(problems)} problem(s)"
    guide = PLUGIN_ROOT / FORMAT_GUIDES[kind]
    return f"{heading}\n{problem_lines}\nFix these (see {guide})."


def kit_file_kinds(path: Path, config: Config) -> dict[str, bool]:
    claude_dir = config.root / ".claude"
    is_markdown = path.suffix == ".md"
    return {
        "spec": path.name == "spec.md" and path.parent.parent == config.specs_dir,
        "outputs": lint_outputs.is_build_output(path, config),
        "decision": is_markdown and path.parent == config.decisions_dir,
        "skill": path.name == "SKILL.md" and path.parent.parent == claude_dir / "skills",
        "rule": is_markdown and path.parent == claude_dir / "rules",
        "agent": is_markdown and path.parent == claude_dir / "agents",
        "changelog": path == claude_dir / "CHANGELOG.md",
    }


def check_css(path: Path, config: Config) -> str | None:
    if config.design is None or path.suffix != ".css" or "node_modules" in path.parts:
        return None
    problems = [
        line for line in check_tokens.check_file(path, config) if not line.startswith("skip")
    ]
    if not problems:
        return None
    guide = relative(config.design.guide, config.root)
    return "\n".join([*problems, f"Fix these now; the tokens and their uses are in {guide}."])


def check_code_shape(path: Path, config: Config) -> str | None:
    if config.architecture is None or "node_modules" in path.parts:
        return None
    problems = check_shape.check_paths([path], config)
    return "\n".join([*problems[:-1], f"Fix these now. {problems[-1]}"]) if problems else None


def lint_build_output(path: Path, config: Config) -> list[str]:
    return lint_outputs.lint(path, config)


def lint_changelog_and_dates(changelog_path: Path, _config: Config) -> list[str]:
    changelog_text = changelog_path.read_text()
    problems = lint_changelog.lint(changelog_text)
    base_text = check_branch_dates.read_base_changelog(check_branch_dates.DEFAULT_BASE)
    # No remote main to compare with, as in a fresh clone offline: skip the branch check.
    date_problem = base_text and check_branch_dates.find_problem(base_text, changelog_text)
    return [*problems, date_problem] if date_problem else problems


def format_and_lint(path: Path, config: Config) -> str | None:
    """Format first, so style never costs a turn; then report what the linter finds."""
    if is_handled(path, config.format):
        assert config.format is not None
        run_command(config.format, path, config.root)
    if not is_handled(path, config.lint):
        return None
    assert config.lint is not None
    lint = run_command(config.lint, path, config.root)
    if lint.returncode == 0:
        return None
    output = (lint.stdout + lint.stderr).strip()
    return f"Lint errors in {relative(path, config.root)}; fix them now:\n{output}"


def is_handled(path: Path, command: OnWrite | None) -> bool:
    return (
        command is not None
        and path.suffix in command.extensions
        and "node_modules" not in path.parts
    )


def run_command(command: OnWrite, path: Path, root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        fill(command.run, file=str(path)),
        shell=True,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def ignoring_config(lint: Callable[[Path], list[str]]) -> Linter:
    return lambda path, _config: lint(path)


LINTERS: dict[str, Linter] = {
    "spec": ignoring_config(lint_spec.lint),
    "outputs": lint_build_output,
    "decision": ignoring_config(lint_decision.lint),
    "skill": ignoring_config(lint_skill.lint),
    "rule": ignoring_config(lint_rule.lint),
    "agent": ignoring_config(lint_agent.lint),
    "changelog": lint_changelog_and_dates,
}


if __name__ == "__main__":
    sys.exit(main())
