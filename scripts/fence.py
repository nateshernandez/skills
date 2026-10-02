#!/usr/bin/env python3
"""PreToolUse hook: keep each subagent's writes inside the fence its agent file declares.

Usage: fence.py   (reads the hook JSON on stdin; registered in hooks/hooks.json)

A kit agent (this plugin's agents/) or a project agent (.claude/agents/) may list globs in its
frontmatter, relative to the project root, fnmatch-style:
  fence-deny:  writes to matching paths are blocked
  fence-allow: writes to anything not matching are blocked
`{acceptance}` and `{probes}` in a glob stand for the config's test paths, with every spec and
lens. Paths are compared by real path, so `/tmp/*` also covers macOS's `/private/tmp`. The main
session, other plugins' agents, and projects without .claude/kit/config.json are not checked.
Bash is checked only for obvious writes (redirects, sed -i, tee, mv, cp, rm, touch); it's a
tripwire, not a sandbox.
A `>` inside quotes, a heredoc body, `=>`, or `->` is not a redirect.
"""

import json
import os
import re
import sys
from enum import Enum
from fnmatch import fnmatch
from itertools import pairwise
from pathlib import Path
from typing import NamedTuple

from kit_config import Config, load_if_set_up, test_glob

KIT_AGENTS_DIR = Path(__file__).resolve().parents[1] / "agents"
KIT_AGENT_PREFIX = "kit:"
FILE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
WRITING_COMMANDS = frozenset(("tee", "rm", "touch", "truncate"))
COPYING_COMMANDS = frozenset(("mv", "cp"))
OPERATOR_CHARS = "|&;<>()"
# Longest first, so `<<-` is not read as `<<` then `-`.
OPERATORS = ("<<<", "<<-", "&>>", ">>", ">&", ">|", "&>", "&&", "||", "<<", "<&", "<>")
SEPARATORS = frozenset(("|", "||", "&&", "&", ";", "\n", "(", ")"))
FILE_REDIRECTS = frozenset((">", ">>", ">|", "&>", "&>>", ">&"))
HEREDOCS = frozenset(("<<", "<<-"))
SED_SCRIPT_FLAGS = ("-e", "-f", "--expression", "--file")
OUTPUT_DEVICE_PREFIX = "/dev/"
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_]\w*=")


class Mode(Enum):
    DENY = "fence-deny"
    ALLOW = "fence-allow"


class Fence(NamedTuple):
    mode: Mode
    globs: list[str]


class Token(NamedTuple):
    text: str
    is_operator: bool = False


def main() -> int:
    if sys.argv[1:]:
        print(__doc__, file=sys.stderr)
        return 1
    hook_input = json.load(sys.stdin)
    agent_type = hook_input.get("agent_type") or ""
    config = load_if_set_up() if agent_type else None
    agent_path = find_agent_file(agent_type, config.root) if config else None
    fence = load_fence(agent_path, config) if config and agent_path else None
    if config is None or fence is None:
        return 0
    tool_input = hook_input.get("tool_input", {})
    tool_name = hook_input.get("tool_name", "")
    blocked_path = find_blocked_path(tool_name, tool_input, fence, config.root)
    if blocked_path is None:
        return 0
    rule = "is locked for" if fence.mode is Mode.DENY else "is outside the fence of"
    print(f"`{blocked_path}` {rule} the {agent_type} agent.", file=sys.stderr)
    print("If the locked file is wrong, stop and report it; don't work around it.", file=sys.stderr)
    if hook_input.get("tool_name") == "Bash":
        print("Not a write to that path? Quote or reword the `>` and retry.", file=sys.stderr)
    return 2


def find_agent_file(agent_type: str, root: Path) -> Path | None:
    """Kit's agents arrive as `kit:<name>`; a project's own, as the bare name."""
    if agent_type.startswith(KIT_AGENT_PREFIX):
        agent_path = KIT_AGENTS_DIR / f"{agent_type.removeprefix(KIT_AGENT_PREFIX)}.md"
    elif ":" in agent_type:
        return None
    else:
        agent_path = root / ".claude" / "agents" / f"{agent_type}.md"
    return agent_path if agent_path.exists() else None


def load_fence(agent_path: Path, config: Config) -> Fence | None:
    frontmatter = agent_path.read_text().split("\n---", 1)[0]
    test_globs = {
        "{acceptance}": test_glob(config.tests.acceptance),
        "{probes}": test_glob(config.tests.probes),
    }
    for mode in Mode:
        globs = list_field(frontmatter, mode.value)
        if globs:
            return Fence(mode, [expand(glob, test_globs) for glob in globs])
    return None


def expand(glob: str, test_globs: dict[str, str]) -> str:
    for placeholder, path_glob in test_globs.items():
        glob = glob.replace(placeholder, path_glob)
    return glob


def list_field(frontmatter: str, field_name: str) -> list[str]:
    values: list[str] = []
    in_field = False
    for line in frontmatter.splitlines():
        if not line.startswith((" ", "\t")):
            in_field = line.startswith(f"{field_name}:")
        elif in_field and line.strip().startswith("- "):
            values.append(line.strip()[2:].strip().strip("\"'"))
    return values


def find_blocked_path(tool_name: str, tool_input: dict, fence: Fence, root: Path) -> str | None:
    if tool_name in FILE_TOOLS:
        raw_paths = [tool_input.get("file_path") or tool_input.get("notebook_path", "")]
    elif tool_name == "Bash":
        raw_paths = bash_write_targets(tool_input.get("command", ""))
    else:
        return None
    for raw_path in raw_paths:
        target = fence_path(raw_path, root)
        if target is not None and is_blocked(target, fence):
            return target
    return None


def bash_write_targets(command: str) -> list[str]:
    tokens = tokenize(command)
    targets = redirect_targets(tokens)
    for words in command_segments(tokens):
        targets += command_write_targets(words)
    return [target for target in targets if not target.startswith(OUTPUT_DEVICE_PREFIX)]


def tokenize(command: str) -> list[Token]:
    """Split a shell command into words and operators, leaving out comments and heredoc bodies."""
    tokens: list[Token] = []
    heredoc_delimiters: list[str] = []
    position = 0
    while position < len(command):
        char = command[position]
        if char == "\n":
            tokens.append(Token(char, is_operator=True))
            position = skip_heredoc_bodies(command, position + 1, heredoc_delimiters)
        elif char.isspace():
            position += 1
        elif char == "#":
            position = end_of_line(command, position)
        elif char in OPERATOR_CHARS:
            operator = read_operator(command, position)
            tokens.append(Token(operator, is_operator=True))
            position += len(operator)
        else:
            word, position = read_word(command, position)
            is_file_descriptor = word.isdigit() and command[position : position + 1] in ("<", ">")
            if tokens and tokens[-1].text in HEREDOCS:
                heredoc_delimiters.append(word)
            if not is_file_descriptor:
                tokens.append(Token(word))
    return tokens


def end_of_line(command: str, position: int) -> int:
    line_end = command.find("\n", position)
    return len(command) if line_end == -1 else line_end


def read_operator(command: str, position: int) -> str:
    return next(
        (operator for operator in OPERATORS if command.startswith(operator, position)),
        command[position],
    )


def read_word(command: str, position: int) -> tuple[str, int]:
    """Read one word with its quotes and escapes removed; return it and where it ended."""
    characters: list[str] = []
    while position < len(command):
        char = command[position]
        is_arrow = char == ">" and characters[-1:] in (["="], ["-"])
        if (char.isspace() or char in OPERATOR_CHARS) and not is_arrow:
            break
        if char in "'\"":
            quoted, position = read_quoted(command, position)
            characters.append(quoted)
        elif char == "\\" and position + 1 < len(command):
            characters.append(command[position + 1].replace("\n", ""))
            position += 2
        else:
            characters.append(char)
            position += 1
    return "".join(characters), position


def read_quoted(command: str, position: int) -> tuple[str, int]:
    quote = command[position]
    characters: list[str] = []
    position += 1
    while position < len(command) and command[position] != quote:
        has_escape = quote == '"' and command[position] == "\\" and position + 1 < len(command)
        if has_escape:
            position += 1
        characters.append(command[position])
        position += 1
    return "".join(characters), position + 1


def skip_heredoc_bodies(command: str, position: int, delimiters: list[str]) -> int:
    for delimiter in delimiters:
        while position < len(command):
            line_end = end_of_line(command, position)
            is_delimiter_line = command[position:line_end].strip() == delimiter
            position = line_end + 1
            if is_delimiter_line:
                break
    delimiters.clear()
    return position


def redirect_targets(tokens: list[Token]) -> list[str]:
    targets: list[str] = []
    for token, following in pairwise(tokens):
        if not token.is_operator or token.text not in FILE_REDIRECTS or following.is_operator:
            continue
        is_descriptor_copy = token.text == ">&" and following.text in ("-", *"0123456789")
        if not is_descriptor_copy:
            targets.append(following.text)
    return targets


def command_segments(tokens: list[Token]) -> list[list[str]]:
    """The words of each simple command, without redirections and their targets."""
    segments: list[list[str]] = [[]]
    is_redirect_target = False
    for token in tokens:
        if token.is_operator and token.text in SEPARATORS:
            segments.append([])
            is_redirect_target = False
        elif token.is_operator:
            is_redirect_target = True
        elif is_redirect_target:
            is_redirect_target = False
        else:
            segments[-1].append(token.text)
    return segments


def command_write_targets(words: list[str]) -> list[str]:
    command_start = next(
        (index for index, word in enumerate(words) if not ASSIGNMENT_RE.match(word)), len(words)
    )
    if command_start == len(words):
        return []
    name = Path(words[command_start]).name
    arguments = words[command_start + 1 :]
    operands = [argument for argument in arguments if not argument.startswith("-")]
    if name in COPYING_COMMANDS:
        return operands[-1:]
    if name == "sed" and any(argument.startswith(("-i", "--in-place")) for argument in arguments):
        return sed_files(arguments)
    return operands if name in WRITING_COMMANDS else []


def sed_files(arguments: list[str]) -> list[str]:
    operands: list[str] = []
    has_script_flag = False
    is_flag_value = False
    for argument in arguments:
        if is_flag_value:
            is_flag_value = False
        elif argument in ("-e", "-f"):
            has_script_flag = is_flag_value = True
        elif argument.startswith("-"):
            has_script_flag |= argument.startswith(SED_SCRIPT_FLAGS)
        else:
            operands.append(argument)
    # Without -e or -f, the first operand is the sed script, not a file.
    return operands if has_script_flag else operands[1:]


def fence_path(raw_path: str, root: Path) -> str | None:
    """The real path, relative to the repo when inside it; None when it holds an unset variable."""
    expanded = os.path.expandvars(Path(raw_path).expanduser().as_posix())
    if "$" in expanded or "`" in expanded:
        return None
    resolved = (root / expanded).resolve()
    if resolved.is_relative_to(root):
        return resolved.relative_to(root).as_posix()
    return resolved.as_posix()


def real_glob(glob: str) -> str:
    """An absolute glob with its literal directory resolved, so `/tmp/*` meets `/private/tmp`."""
    if not glob.startswith("/"):
        return glob
    wildcard_at = min((glob.find(char) for char in "*?[" if char in glob), default=len(glob))
    directory, _, name_prefix = glob[:wildcard_at].rpartition("/")
    real_directory = Path(directory or "/").resolve().as_posix().rstrip("/")
    return f"{real_directory}/{name_prefix}{glob[wildcard_at:]}"


def is_blocked(target: str, fence: Fence) -> bool:
    matches = any(fnmatch(target, real_glob(glob)) for glob in fence.globs)
    return matches if fence.mode is Mode.DENY else not matches


if __name__ == "__main__":
    sys.exit(main())
