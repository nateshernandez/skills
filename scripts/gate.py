#!/usr/bin/env python3
"""Run the build gate for one spec, using the commands in .claude/kit/config.json.

The task gate, which every task runs: `check`, then this spec's acceptance tests and probes.
Tests naming a behavior that another unfinished task covers (the current task's own are kept)
are skipped, and so are the `<n>.outcome` probes, which judge the whole feature. The full gate,
run once per spec after the last review round: `check_full`, then the spec's acceptance tests
and probes for every delivered behavior. Both run check_tokens.py after the check when the
config has `design`.

Each step's output goes to `kit-gate-<spec>-<scope>.log` in the temp dir. A red run prints the
failed step, that path, the failing test titles, and the log's last lines; read the log, don't
rerun the gate. A green run stamps the working tree; a rerun on the same tree is skipped. Gates
run one at a time, and each gets a free port in KIT_PORT so a test server is never a stale one.

Usage:
  gate.py SPEC_ID          task gate for one spec; exit 1 when red
  gate.py SPEC_ID --full   full gate for one spec; exit 1 when red
  gate.py --hook           SubagentStop hook for kit's builder agent: task gate for every spec
                           with `status: building`; exit 2 (keep working) when red, at most
                           3 times in a row
"""

import fcntl
import hashlib
import json
import os
import random
import re
import shlex
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Literal, NamedTuple

from kit_config import Config, ConfigError, fill, load, load_if_set_up, relative

BUILDER_AGENT = "kit:builder"
CHECK_TOKENS = Path(__file__).resolve().parent / "check_tokens.py"
OUTPUT_TAIL_LINES = 25
MAX_LISTED_TESTS = 15
MAX_CONSECUTIVE_BLOCKS = 3
MAX_PORT_ATTEMPTS = 100
PORT_BLOCK_SIZE = 4
STATUS_BUILDING_RE = re.compile(r"^status:\s*building\s*$", re.MULTILINE)
ACCEPTANCE_TITLE_RE = re.compile(r"\b(?:test|it)\(\s*[\"'`](\d+\.B\d+)\b")
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
NOISE_LINE_RE = re.compile(r"^\s*\[WebServer\]|\(node:\d+\)|--trace-warnings")
FAILURE_TITLE_RES = {
    "playwright": re.compile(r"^\s+\d+\) (\[[^\]]+\] \u203a \S.*)$"),
    "vitest": re.compile(r"^\s*FAIL\s+(\S.*)$"),
    "jest": re.compile(r"^\s+\u25cf (\S.*\u203a.*)$"),
}

GateScope = Literal["task", "full"]


class GateStep(NamedTuple):
    name: str
    command: str


class GateResult(NamedTuple):
    failed_step: str | None
    output_tail: str
    test_titles: tuple[str, ...] = ()
    log_path: Path | None = None
    seconds: float = 0.0
    was_skipped: bool = False

    @property
    def is_green(self) -> bool:
        return self.failed_step is None


def main() -> int:
    arguments = sys.argv[1:]
    if arguments == ["--hook"]:
        return run_hook()
    if len(arguments) not in (1, 2) or arguments[1:] not in ([], ["--full"]):
        print(__doc__, file=sys.stderr)
        return 1
    try:
        config = load()
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    spec_id = arguments[0]
    if not (config.specs_dir / spec_id / "spec.md").exists():
        print(f"specs/{spec_id}/spec.md doesn't exist", file=sys.stderr)
        return 1
    scope: GateScope = "full" if arguments[1:] == ["--full"] else "task"
    result = run_gate(config, spec_id, scope, task_id=None)
    if result.is_green:
        print(f"{spec_id}: {scope} {describe_green(result)}")
        return 0
    print(format_failure(result), file=sys.stderr)
    return 1


def run_hook() -> int:
    hook_input = json.load(sys.stdin)
    if hook_input.get("agent_type") != BUILDER_AGENT:
        return 0
    config = load_if_set_up()
    if config is None or is_gate_running(config):
        return 0
    counter_path = block_counter_path(hook_input)
    building_ids = [
        spec_path.parent.name
        for spec_path in sorted(config.specs_dir.glob("*/spec.md"))
        if STATUS_BUILDING_RE.search(spec_path.read_text())
    ]
    for spec_id in building_ids:
        result = run_gate(config, spec_id, "task", task_id=None)
        if not result.is_green:
            return block_stop(result, counter_path)
    counter_path.unlink(missing_ok=True)
    return 0


def temp_path(config: Config, name: str) -> Path:
    # Keyed by project, so two projects on one machine never share a lock, stamp, or log.
    project_key = hashlib.sha1(str(config.root).encode()).hexdigest()[:8]
    return Path(tempfile.gettempdir()) / f"kit-{project_key}-{name}"


def is_gate_running(config: Config) -> bool:
    with temp_path(config, "gate.lock").open("w") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        return False


def block_counter_path(hook_input: dict) -> Path:
    run_id = hook_input.get("agent_id") or hook_input.get("session_id", "unknown")
    return Path(tempfile.gettempdir()) / f"kit-gate-blocks-{run_id}"


def block_stop(result: GateResult, counter_path: Path) -> int:
    block_count = int(counter_path.read_text()) + 1 if counter_path.exists() else 1
    if block_count > MAX_CONSECUTIVE_BLOCKS:
        counter_path.unlink()
        print(f"gate still red after {MAX_CONSECUTIVE_BLOCKS} tries; stopping", file=sys.stderr)
        return 0
    counter_path.write_text(str(block_count))
    print(format_failure(result), file=sys.stderr)
    print("The gate is red: fix it before stopping, or record the blocker.", file=sys.stderr)
    return 2


def acceptance_test_ids(config: Config, spec_id: str) -> list[str]:
    test_path = config.acceptance_path(spec_id)
    return ACCEPTANCE_TITLE_RE.findall(test_path.read_text()) if test_path.exists() else []


def run_gate(config: Config, spec_id: str, scope: GateScope, task_id: str | None) -> GateResult:
    """`task_id` is the task being marked; its behaviors run even though it isn't passing yet."""
    steps = gate_steps(config, spec_id, scope, task_id)
    log_path = temp_path(config, f"gate-{spec_id}-{scope}.log")
    stamp_path = temp_path(config, f"gate-green-{spec_id}-{scope}")
    stamp = f"{working_tree_hash(config.root)} {json.dumps([step.command for step in steps])}"
    with temp_path(config, "gate.lock").open("w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        # Checked under the lock: a gate that waited may find the one before it already passed.
        if stamp_path.exists() and stamp_path.read_text() == stamp:
            return GateResult(None, "", was_skipped=True)
        started = time.monotonic()
        result = run_steps(config, steps, log_path)._replace(seconds=time.monotonic() - started)
        if result.is_green:
            stamp_path.write_text(stamp)
    return result


def describe_green(result: GateResult) -> str:
    if result.was_skipped:
        return "gate green (tree unchanged since its last green run; skipped)"
    return f"gate green in {round(result.seconds / 60, 1)} min"


def format_failure(result: GateResult) -> str:
    lines = [
        f"gate red at `{result.failed_step}` after {round(result.seconds / 60, 1)} min",
        f"full log: {result.log_path}",
    ]
    if result.test_titles:
        lines.append("failing tests:")
        lines += [f"  {title}" for title in result.test_titles[:MAX_LISTED_TESTS]]
        unlisted_count = len(result.test_titles) - MAX_LISTED_TESTS
        if unlisted_count > 0:
            lines.append(f"  ... and {unlisted_count} more in the log")
    lines += ["last output:", result.output_tail]
    return "\n".join(lines)


def gate_steps(
    config: Config, spec_id: str, scope: GateScope, task_id: str | None
) -> list[GateStep]:
    tasks = load_tasks(config, spec_id)
    if scope == "full":
        skipped_ids = undelivered_behavior_ids(tasks)
        steps = [GateStep("check_full", config.check_full)]
    else:
        skipped_ids = [*waiting_behavior_ids(tasks, task_id), outcome_probe_id(spec_id)]
        steps = [GateStep("check", config.check)]
    if config.design:
        steps.append(GateStep("design tokens", f"python3 {shlex.quote(str(CHECK_TOKENS))}"))
    test_files = spec_test_files(config, spec_id)
    if test_files:
        command = fill(config.tests.run, files=test_files, grep=grep_excluding(skipped_ids))
        steps.append(GateStep(f"{spec_id} tests", command))
    return steps


def load_tasks(config: Config, spec_id: str) -> list[dict]:
    tasks_path = config.specs_dir / spec_id / "tasks.json"
    return json.loads(tasks_path.read_text())["tasks"] if tasks_path.exists() else []


def spec_test_files(config: Config, spec_id: str) -> list[str]:
    paths = [config.acceptance_path(spec_id), *config.probe_paths(spec_id)]
    return [relative(path, config.root) for path in paths if path.exists()]


def undelivered_behavior_ids(tasks: list[dict]) -> list[str]:
    delivered = {behavior_id for task in tasks if task["passes"] for behavior_id in task["covers"]}
    planned = {behavior_id for task in tasks for behavior_id in task["covers"]}
    return sorted(planned - delivered)


def outcome_probe_id(spec_id: str) -> str:
    # Outcome probes check the whole feature, so they run only in the full gate.
    return f"{int(spec_id.split('-', 1)[0])}.outcome"


def waiting_behavior_ids(tasks: list[dict], task_id: str | None) -> list[str]:
    # A fix task's probes fail until it lands, even for a behavior an earlier task delivered;
    # running them sooner would block every other task. Two fix tasks may cover one behavior, so
    # the current task keeps its own: the hook passes no task and gates the first unfinished one.
    unfinished = [task for task in tasks if not task["passes"]]
    current_id = task_id or (unfinished[0]["id"] if unfinished else None)
    own_ids = {
        behavior_id for task in tasks if task["id"] == current_id for behavior_id in task["covers"]
    }
    waiting_ids = {
        behavior_id
        for task in unfinished
        if task["id"] != current_id
        for behavior_id in task["covers"]
    }
    return sorted(waiting_ids - own_ids)


def grep_excluding(skipped_ids: list[str]) -> str:
    """A title regex for the runner's grep option: every test except the skipped IDs."""
    if not skipped_ids:
        return "^"
    # The lookbehind keeps 1.B1 from matching inside 11.B1; the \b keeps it out of 1.B11.
    alternatives = "|".join(map(re.escape, skipped_ids))
    return rf"^(?!.*(?<![\d.])(?:{alternatives})\b)"


def working_tree_hash(root: Path) -> str:
    # A throwaway index hashes tracked and untracked files alike, without touching the real one.
    # specs/ holds logs and task state, which no check reads.
    with tempfile.TemporaryDirectory() as scratch_dir:
        git_env = {**os.environ, "GIT_INDEX_FILE": str(Path(scratch_dir) / "index")}
        git(root, ["add", "--all", "--", ".", ":(exclude)specs"], git_env)
        return git(root, ["write-tree"], git_env)


def git(root: Path, git_args: list[str], git_env: dict[str, str]) -> str:
    completed = subprocess.run(
        ["git", *git_args], cwd=root, env=git_env, capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


def run_steps(config: Config, steps: list[GateStep], log_path: Path) -> GateResult:
    # NO_COLOR keeps ANSI codes out of test titles; FORCE_COLOR would override it.
    step_env = {key: value for key, value in os.environ.items() if key != "FORCE_COLOR"}
    step_env |= {"KIT_PORT": str(free_port()), "NO_COLOR": "1"}
    log_path.write_bytes(b"")
    for step in steps:
        log_start = log_path.stat().st_size
        if run_step(config.root, step, step_env, log_path) != 0:
            step_output = log_path.read_bytes()[log_start:].decode(errors="replace")
            report = summarize_output(step_output, config.tests.runner)
            return GateResult(step.name, report.tail, report.test_titles, log_path)
    return GateResult(None, "")


def run_step(root: Path, step: GateStep, step_env: dict[str, str], log_path: Path) -> int:
    with log_path.open("ab") as log_file:
        log_file.write(f"$ {step.command}\n".encode())
        log_file.flush()
        completed = subprocess.run(
            step.command,
            shell=True,
            cwd=root,
            env=step_env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            check=False,
        )
    # Piped servers leave NUL bytes that make tools treat the log as binary.
    log_bytes = log_path.read_bytes()
    log_path.write_bytes(log_bytes.replace(b"\0", b""))
    return completed.returncode


class FailureSummary(NamedTuple):
    test_titles: tuple[str, ...]
    tail: str


def summarize_output(step_output: str, runner: str) -> FailureSummary:
    lines = ANSI_RE.sub("", step_output).replace("\r", "").splitlines()
    quiet_lines = [line for line in lines if not NOISE_LINE_RE.search(line)]
    title_re = FAILURE_TITLE_RES[runner]
    titles = dict.fromkeys(
        title_match.group(1).rstrip("─ ")
        for title_match in map(title_re.match, lines)
        if title_match
    )
    return FailureSummary(tuple(titles), "\n".join(quiet_lines[-OUTPUT_TAIL_LINES:]))


def free_port() -> int:
    # A block of free ports, so a test setup that needs a few (app, stand-ins) can count up.
    for _ in range(MAX_PORT_ATTEMPTS):
        base_port = random.randint(10_000, 60_000)
        if all(is_port_free(base_port + offset) for offset in range(PORT_BLOCK_SIZE)):
            return base_port
    message = f"no block of {PORT_BLOCK_SIZE} free ports found"
    raise RuntimeError(message)


def is_port_free(port: int) -> bool:
    with socket.socket() as probe:
        try:
            probe.bind(("", port))
        except OSError:
            return False
        return True


if __name__ == "__main__":
    sys.exit(main())
