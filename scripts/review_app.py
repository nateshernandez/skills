#!/usr/bin/env python3
"""Start or stop the app reviewers share during a review round (`app` in .claude/kit/config.json).

Usage:
  review_app.py start   run `app.serve` in the background; return once `app.url` answers
  review_app.py stop    stop the app this script started

`start` prints `READY <url>`, or the server's last log lines when it exits or never answers.
Without an `app` in the config it prints `no app configured` and exits 0: reviewers run tests
directly. The server's output goes to `kit-<project>-app.log` in the temp dir.
"""

import contextlib
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from gate import temp_path
from kit_config import Config, ConfigError, load

STARTUP_LIMIT_SECONDS = 15 * 60
POLL_SECONDS = 2
LOG_TAIL_LINES = 25


def main() -> int:
    if sys.argv[1:] not in (["start"], ["stop"]):
        print(__doc__, file=sys.stderr)
        return 1
    try:
        config = load()
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    if config.app is None:
        print("no app configured; reviewers run tests directly")
        return 0
    return start(config) if sys.argv[1] == "start" else stop(config)


def start(config: Config) -> int:
    assert config.app is not None
    if is_answering(config.app.url):
        print(f"READY {config.app.url} (already running)")
        return 0
    log_path = temp_path(config, "app.log")
    with log_path.open("wb") as log_file:
        server = subprocess.Popen(
            config.app.serve,
            shell=True,
            cwd=config.root,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    temp_path(config, "app.pid").write_text(str(server.pid))
    deadline = time.monotonic() + STARTUP_LIMIT_SECONDS
    while time.monotonic() < deadline:
        if server.poll() is not None:
            print(f"`app.serve` exited with {server.returncode}; log: {log_path}", file=sys.stderr)
            print(log_tail(log_path), file=sys.stderr)
            return 1
        if is_answering(config.app.url):
            print(f"READY {config.app.url}")
            return 0
        time.sleep(POLL_SECONDS)
    print(f"{config.app.url} didn't answer within 15 min; log: {log_path}", file=sys.stderr)
    print(log_tail(log_path), file=sys.stderr)
    return 1


def stop(config: Config) -> int:
    pid_path = temp_path(config, "app.pid")
    if not pid_path.exists():
        print("no review app running")
        return 0
    # The server runs in its own session, so the group holds it and anything it started.
    with contextlib.suppress(ProcessLookupError):
        os.killpg(int(pid_path.read_text()), signal.SIGTERM)
    pid_path.unlink()
    print("review app stopped")
    return 0


def is_answering(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=POLL_SECONDS):
            return True
    except urllib.error.HTTPError:
        return True  # any HTTP response means the server is up
    except (urllib.error.URLError, OSError):
        return False


def log_tail(log_path: Path) -> str:
    lines = log_path.read_text(errors="replace").splitlines()
    return "\n".join(lines[-LOG_TAIL_LINES:])


if __name__ == "__main__":
    sys.exit(main())
