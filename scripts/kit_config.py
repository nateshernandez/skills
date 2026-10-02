"""Load a project's kit config, `.claude/kit/config.json`, and resolve the paths it names.

Imported by the other scripts; not run on its own. docs/configuration.md documents every field.
"""

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import NamedTuple

CONFIG_PATH = Path(".claude") / "kit" / "config.json"
CHECKLISTS_PATH = Path(".claude") / "kit" / "checklists"
SPECS_PATH = Path("specs")
DECISIONS_PATH = Path("docs") / "decisions"
RUNNERS = ("playwright", "vitest", "jest")
LENSES = ("quality", "ux", "security", "code")
TOP_LEVEL_FIELDS = frozenset(
    ("check", "check_full", "tests", "app", "screenshots", "audit", "format", "lint")
)


class ConfigError(Exception):
    """The config is missing or malformed; the message names the field and the fix."""


class Tests(NamedTuple):
    runner: str
    acceptance: str
    probes: str
    run: str


class App(NamedTuple):
    serve: str
    url: str
    env: dict[str, str]


class OnWrite(NamedTuple):
    extensions: tuple[str, ...]
    run: str


class Config(NamedTuple):
    root: Path
    check: str
    check_full: str
    tests: Tests
    app: App | None
    screenshots: str | None
    audit: str | None
    format: OnWrite | None
    lint: OnWrite | None

    @property
    def specs_dir(self) -> Path:
        return self.root / SPECS_PATH

    @property
    def decisions_dir(self) -> Path:
        return self.root / DECISIONS_PATH

    def acceptance_path(self, spec_id: str) -> Path:
        return self.root / self.tests.acceptance.replace("{spec}", spec_id)

    def probe_path(self, spec_id: str, lens: str) -> Path:
        return self.root / self.tests.probes.replace("{spec}", spec_id).replace("{lens}", lens)

    def probe_paths(self, spec_id: str) -> list[Path]:
        return [path for lens in LENSES if (path := self.probe_path(spec_id, lens)).exists()]


def test_glob(template: str) -> str:
    """A repo-relative glob for every file a test path template names, like `tests/probes/*-*`."""
    return template.replace("{spec}", "*").replace("{lens}", "*")


def project_root() -> Path:
    """The project being worked on: Claude Code's project dir, else the enclosing git repo."""
    if project_dir := os.environ.get("CLAUDE_PROJECT_DIR"):
        return Path(project_dir).resolve()
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False
    )
    return Path(completed.stdout.strip() or ".").resolve()


def load(root: Path | None = None) -> Config:
    root = root or project_root()
    config_path = root / CONFIG_PATH
    if not config_path.exists():
        message = f"{CONFIG_PATH} doesn't exist in {root}; run /kit:setup first"
        raise ConfigError(message)
    try:
        raw = json.loads(config_path.read_text())
    except json.JSONDecodeError as error:
        message = f"{CONFIG_PATH}: invalid JSON at line {error.lineno}: {error.msg}"
        raise ConfigError(message) from error
    return parse(raw, root)


def load_if_set_up(root: Path | None = None) -> Config | None:
    """For hooks: None when this project hasn't run /kit:setup, so kit stays out of its way."""
    root = root or project_root()
    return load(root) if (root / CONFIG_PATH).exists() else None


def parse(raw: dict, root: Path) -> Config:
    unknown_fields = sorted(set(raw) - TOP_LEVEL_FIELDS)
    if unknown_fields:
        message = f"{CONFIG_PATH}: unknown fields {unknown_fields}; see docs/configuration.md"
        raise ConfigError(message)
    return Config(
        root=root,
        check=required_text(raw, "check"),
        check_full=required_text(raw, "check_full"),
        tests=parse_tests(raw.get("tests")),
        app=parse_app(raw["app"]) if "app" in raw else None,
        screenshots=optional_text(raw, "screenshots"),
        audit=optional_text(raw, "audit"),
        format=parse_on_write(raw["format"], "format") if "format" in raw else None,
        lint=parse_on_write(raw["lint"], "lint") if "lint" in raw else None,
    )


def parse_tests(raw_tests: object) -> Tests:
    if not isinstance(raw_tests, dict):
        message = f"{CONFIG_PATH}: `tests` must be an object with runner, acceptance, probes, run"
        raise ConfigError(message)
    tests = Tests(
        runner=required_text(raw_tests, "runner", "tests."),
        acceptance=required_text(raw_tests, "acceptance", "tests."),
        probes=required_text(raw_tests, "probes", "tests."),
        run=required_text(raw_tests, "run", "tests."),
    )
    if tests.runner not in RUNNERS:
        message = f"{CONFIG_PATH}: tests.runner must be one of {list(RUNNERS)}"
        raise ConfigError(message)
    for field_name, placeholders in (
        ("acceptance", ("{spec}",)),
        ("probes", ("{spec}", "{lens}")),
        ("run", ("{files}", "{grep}")),
    ):
        missing = [name for name in placeholders if name not in getattr(tests, field_name)]
        if missing:
            message = f"{CONFIG_PATH}: tests.{field_name} must contain {', '.join(missing)}"
            raise ConfigError(message)
    return tests


def parse_app(raw_app: object) -> App:
    if not isinstance(raw_app, dict):
        message = f"{CONFIG_PATH}: `app` must be an object with serve and url"
        raise ConfigError(message)
    raw_env = raw_app.get("env", {})
    is_text_map = isinstance(raw_env, dict) and all(
        isinstance(value, str) for value in raw_env.values()
    )
    if not is_text_map:
        message = f"{CONFIG_PATH}: app.env must map variable names to strings"
        raise ConfigError(message)
    return App(
        serve=required_text(raw_app, "serve", "app."),
        url=required_text(raw_app, "url", "app."),
        env=raw_env,
    )


def parse_on_write(raw_command: object, field_name: str) -> OnWrite:
    if not isinstance(raw_command, dict):
        message = f"{CONFIG_PATH}: `{field_name}` must be an object with extensions and run"
        raise ConfigError(message)
    extensions = raw_command.get("extensions")
    if not isinstance(extensions, list) or not all(
        isinstance(extension, str) and extension.startswith(".") for extension in extensions
    ):
        message = f'{CONFIG_PATH}: {field_name}.extensions must be a list like [".ts", ".tsx"]'
        raise ConfigError(message)
    run = required_text(raw_command, "run", f"{field_name}.")
    if "{file}" not in run:
        message = f"{CONFIG_PATH}: {field_name}.run must contain {{file}}"
        raise ConfigError(message)
    return OnWrite(tuple(extensions), run)


def required_text(raw: dict, field_name: str, prefix: str = "") -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        message = f"{CONFIG_PATH}: `{prefix}{field_name}` is required and must be a command string"
        raise ConfigError(message)
    return value


def optional_text(raw: dict, field_name: str) -> str | None:
    if field_name not in raw:
        return None
    return required_text(raw, field_name)


def fill(template: str, **values: str | list[str]) -> str:
    """Fill `{name}` placeholders, shell-quoting each value; a list becomes quoted words."""
    command = template
    for name, value in values.items():
        words = value if isinstance(value, list) else [value]
        command = command.replace(f"{{{name}}}", " ".join(map(shlex.quote, words)))
    return command


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
