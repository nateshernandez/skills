#!/usr/bin/env python3
"""Run one spec's tests the way reviewers do: every test, against the review app when there is one.

Usage: run_tests.py SPEC_ID [FILE ...]
  No files: the spec's acceptance tests and probes. Nothing is skipped, and nothing is stamped.
  When the config has an `app`, its `env` is set and KIT_APP_URL holds its url.
Prints `pass`, or the failing test titles and the log's last lines; exit 1 when a test fails.
"""

import os
import sys

from gate import GateStep, format_failure, run_steps, spec_test_files, temp_path
from kit_config import ConfigError, fill, load


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 1
    spec_id, *test_files = sys.argv[1:]
    try:
        config = load()
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    missing = [path for path in test_files if not (config.root / path).exists()]
    if missing:
        print(f"no such test file: {', '.join(missing)}", file=sys.stderr)
        return 1
    test_files = test_files or spec_test_files(config, spec_id)
    if not test_files:
        print(f"{spec_id} has no acceptance tests or probes yet", file=sys.stderr)
        return 1
    if config.app is not None:
        os.environ.update({**config.app.env, "KIT_APP_URL": config.app.url})
    step = GateStep(f"{spec_id} tests", fill(config.tests.run, files=test_files, grep="^"))
    log_path = temp_path(config, f"tests-{spec_id}-{os.getpid()}.log")
    result = run_steps(config, [step], log_path)
    if result.is_green:
        print(f"pass: {' '.join(test_files)}")
        return 0
    print(format_failure(result._replace(log_path=log_path)), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
