"""Load a project's kit config, `.claude/kit/config.json`, and resolve the paths it names.

Imported by the other scripts; not run on its own. docs/configuration.md documents every field.
"""

import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Literal, NamedTuple, get_args

CONFIG_PATH = Path(".claude") / "kit" / "config.json"
CHECKLISTS_PATH = Path(".claude") / "kit" / "checklists"
SPECS_PATH = Path("specs")
DECISIONS_PATH = Path("docs") / "decisions"
RUNNERS = ("playwright", "vitest", "jest")
LENSES = ("quality", "ux", "security", "code")
TOP_LEVEL_FIELDS = frozenset(
    (
        *("check", "check_full", "tests", "app", "screenshots", "audit", "format", "lint"),
        *("design", "architecture", "build"),
    )
)
DESIGN_FIELDS = frozenset(("guide", "tokens", "gallery", "contrast", "themes"))
ARCHITECTURE_FIELDS = frozenset(
    (
        *("guide", "modules", "module_files", "module_folders"),
        *("sources", "exempt", "max_lines", "baseline"),
    )
)
DEFAULT_MAX_LINES = 250
BUILD_FIELDS = frozenset(("mode", "turbo_model"))
TEXT_CONTRAST = 4.5
SPEC_MODE_RE = re.compile(r"^mode:\s*(\S+)", re.MULTILINE)
CONTRAST_PAIR_RE = re.compile(r"^([\w-]+) on ([\w-]+)(?: (\d+(?:\.\d+)?))?$")


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


class ContrastPair(NamedTuple):
    foreground: str
    background: str
    minimum: float


ThemeName = Literal["light", "dark"]
THEME_NAMES: tuple[ThemeName, ...] = get_args(ThemeName)


class Design(NamedTuple):
    guide: Path
    tokens: Path
    gallery: str | None
    contrast: tuple[ContrastPair, ...]
    themes: tuple[ThemeName, ...]


class Architecture(NamedTuple):
    guide: Path
    modules: Path
    module_files: tuple[str, ...]
    module_folders: dict[str, tuple[str, ...]]
    sources: tuple[str, ...]
    exempt: tuple[str, ...]
    max_lines: int
    baseline: Path | None


BuildMode = Literal["standard", "turbo"]


class Build(NamedTuple):
    mode: BuildMode
    turbo_model: str | None


DEFAULT_BUILD = Build(mode="standard", turbo_model=None)


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
    design: Design | None
    architecture: Architecture | None
    build: Build

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
        design=parse_design(raw["design"], root) if "design" in raw else None,
        architecture=(
            parse_architecture(raw["architecture"], root) if "architecture" in raw else None
        ),
        build=parse_build(raw["build"]) if "build" in raw else DEFAULT_BUILD,
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


def parse_design(raw_design: object, root: Path) -> Design:
    if not isinstance(raw_design, dict):
        message = f"{CONFIG_PATH}: `design` must be an object with guide and tokens"
        raise ConfigError(message)
    unknown_fields = sorted(set(raw_design) - DESIGN_FIELDS)
    if unknown_fields:
        message = (
            f"{CONFIG_PATH}: unknown design fields {unknown_fields}; see docs/configuration.md"
        )
        raise ConfigError(message)
    gallery = raw_design.get("gallery")
    if gallery is not None and not (isinstance(gallery, str) and gallery.startswith("/")):
        message = f'{CONFIG_PATH}: design.gallery must be a route like "/design"'
        raise ConfigError(message)
    return Design(
        guide=root / required_text(raw_design, "guide", "design.", "a path"),
        tokens=root / required_text(raw_design, "tokens", "design.", "a path"),
        gallery=gallery,
        contrast=parse_contrast(raw_design.get("contrast", [])),
        themes=parse_themes(raw_design.get("themes", list(THEME_NAMES))),
    )


def parse_themes(raw_themes: object) -> tuple[ThemeName, ...]:
    raw_list = raw_themes if isinstance(raw_themes, list) else []
    themes: tuple[ThemeName, ...] = tuple(t for t in THEME_NAMES if t in raw_list)
    # Equal lengths rule out duplicates and unknown names alike.
    if not themes or len(themes) != len(raw_list):
        message = f'{CONFIG_PATH}: design.themes must be ["light", "dark"], ["light"], or ["dark"]'
        raise ConfigError(message)
    return themes


def configured_themes(config: Config, flag: ThemeName | None) -> tuple[ThemeName, ...]:
    """The themes a check covers: `--theme` first, then `design.themes`, else both."""
    if flag is not None:
        return (flag,)
    return config.design.themes if config.design else THEME_NAMES


def split_theme_flag(arguments: list[str]) -> tuple[ThemeName | None, list[str]]:
    """Pull `--theme=light` or `--theme=dark` out of a script's arguments."""
    flags = [argument for argument in arguments if argument.startswith("--theme")]
    rest = [argument for argument in arguments if argument not in flags]
    matches: list[ThemeName] = [t for t in THEME_NAMES if flags == [f"--theme={t}"]]
    if flags and not matches:
        message = "pass one --theme=light or --theme=dark"
        raise ConfigError(message)
    return (matches[0] if matches else None), rest


def parse_build(raw_build: object) -> Build:
    if not isinstance(raw_build, dict):
        message = f"{CONFIG_PATH}: `build` must be an object with mode and turbo_model"
        raise ConfigError(message)
    unknown_fields = sorted(set(raw_build) - BUILD_FIELDS)
    if unknown_fields:
        message = f"{CONFIG_PATH}: unknown build fields {unknown_fields}; see docs/configuration.md"
        raise ConfigError(message)
    mode = raw_build.get("mode", DEFAULT_BUILD.mode)
    if mode not in get_args(BuildMode):
        message = f"{CONFIG_PATH}: build.mode must be one of {list(get_args(BuildMode))}"
        raise ConfigError(message)
    turbo_model = raw_build.get("turbo_model")
    if turbo_model is not None and not (
        isinstance(turbo_model, str) and re.fullmatch(r"[\w.:\[\]-]+", turbo_model)
    ):
        message = f'{CONFIG_PATH}: build.turbo_model must be a model name like "sonnet"'
        raise ConfigError(message)
    return Build(mode, turbo_model)


def parse_contrast(raw_pairs: object) -> tuple[ContrastPair, ...]:
    if not isinstance(raw_pairs, list):
        message = f'{CONFIG_PATH}: design.contrast must be a list like ["link on background"]'
        raise ConfigError(message)
    pairs = []
    for raw_pair in raw_pairs:
        match = CONTRAST_PAIR_RE.match(raw_pair) if isinstance(raw_pair, str) else None
        if match is None:
            message = (
                f"{CONFIG_PATH}: design.contrast entry {raw_pair!r} must read"
                ' "<token> on <token>" with an optional minimum ratio, like "ring on background 3"'
            )
            raise ConfigError(message)
        foreground, background, minimum = match.groups()
        pairs.append(ContrastPair(foreground, background, float(minimum or TEXT_CONTRAST)))
    return tuple(pairs)


def parse_architecture(raw_architecture: object, root: Path) -> Architecture:
    if not isinstance(raw_architecture, dict):
        message = f"{CONFIG_PATH}: `architecture` must be an object; see docs/configuration.md"
        raise ConfigError(message)
    unknown_fields = sorted(set(raw_architecture) - ARCHITECTURE_FIELDS)
    if unknown_fields:
        message = (
            f"{CONFIG_PATH}: unknown architecture fields {unknown_fields};"
            " see docs/configuration.md"
        )
        raise ConfigError(message)
    max_lines = raw_architecture.get("max_lines", DEFAULT_MAX_LINES)
    if not isinstance(max_lines, int) or isinstance(max_lines, bool) or max_lines < 1:
        message = f"{CONFIG_PATH}: architecture.max_lines must be a whole number above 0"
        raise ConfigError(message)
    baseline = raw_architecture.get("baseline")
    return Architecture(
        guide=root / required_text(raw_architecture, "guide", "architecture.", "a path"),
        modules=root / required_text(raw_architecture, "modules", "architecture.", "a path"),
        module_files=text_list(raw_architecture, "module_files"),
        module_folders=parse_module_folders(raw_architecture.get("module_folders")),
        sources=text_list(raw_architecture, "sources"),
        exempt=text_list(raw_architecture, "exempt", is_required=False),
        max_lines=max_lines,
        baseline=root / required_text(raw_architecture, "baseline", "architecture.", "a path")
        if baseline is not None
        else None,
    )


def parse_module_folders(raw_folders: object) -> dict[str, tuple[str, ...]]:
    is_folder_map = isinstance(raw_folders, dict) and all(
        isinstance(globs, list) and globs and all(isinstance(glob, str) for glob in globs)
        for globs in raw_folders.values()
    )
    if not is_folder_map:
        message = (
            f"{CONFIG_PATH}: architecture.module_folders must map each folder to its file globs,"
            ' like {"domain": ["*.ts"]}'
        )
        raise ConfigError(message)
    assert isinstance(raw_folders, dict)
    return {folder: tuple(globs) for folder, globs in raw_folders.items()}


def text_list(raw: dict, field_name: str, *, is_required: bool = True) -> tuple[str, ...]:
    values = raw.get(field_name, None if is_required else [])
    is_text_list = isinstance(values, list) and all(isinstance(value, str) for value in values)
    if not is_text_list or (is_required and not values):
        count = "a list of one or more" if is_required else "a list of"
        message = f"{CONFIG_PATH}: architecture.{field_name} must be {count} strings"
        raise ConfigError(message)
    assert isinstance(values, list)
    return tuple(values)


def required_text(
    raw: dict, field_name: str, prefix: str = "", kind: str = "a command string"
) -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        message = f"{CONFIG_PATH}: `{prefix}{field_name}` is required and must be {kind}"
        raise ConfigError(message)
    return value


def optional_text(raw: dict, field_name: str) -> str | None:
    if field_name not in raw:
        return None
    return required_text(raw, field_name)


def spec_mode(spec_dir: Path) -> str | None:
    """The spec's own `mode:` field; a spec without one builds in the config's `build.mode`."""
    mode_match = SPEC_MODE_RE.search((spec_dir / "spec.md").read_text())
    return mode_match.group(1) if mode_match else None


def fill(template: str, **values: str | list[str]) -> str:
    """Fill `{name}` placeholders, shell-quoting each value; a list becomes quoted words."""
    command = template
    for name, value in values.items():
        words = value if isinstance(value, list) else [value]
        command = command.replace(f"{{{name}}}", " ".join(map(shlex.quote, words)))
    return command


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
