#!/usr/bin/env python3
"""Check the colour tokens' contrast in each theme, and that no other CSS file holds a colour.

Usage: check_tokens.py [--theme=light|dark] [CSS_FILE ...]
  No files: contrast in the config's `design.tokens`, then raw colours in every tracked .css
  file outside specs/. Given files: the tokens file and anything under specs/ (a prototype) get
  the contrast check; any other file gets the raw-colour check. Without `design` in the config,
  given files all get the contrast check, as a design system's first prototype needs.

Pairs: foreground on background, <name>-foreground on <name>, <name> on <name>-bg, and each
`design.contrast` entry, in each of `design.themes` (light and dark when unset); `--theme`
checks only that one, as a single-theme app's first prototype needs. docs/configuration.md says
how the light and dark themes are read.
Prints one line per problem and per pair it couldn't read; exit 1 on a problem.
"""

import math
import re
import subprocess
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import NamedTuple

from kit_config import (
    TEXT_CONTRAST,
    Config,
    ConfigError,
    ContrastPair,
    ThemeName,
    configured_themes,
    load,
    relative,
    split_theme_flag,
)

MAX_VAR_DEPTH = 10
# OKLCH chroma and OKLab a/b written as percentages are fractions of 0.4 (CSS Color 4).
OKLAB_PERCENT_SCALE = 0.4
THEME_ROOT_RE = re.compile(r":root|\bhtml\b|^@theme|\.dark\b|\.light\b|data-theme", re.IGNORECASE)
VAR_RE = re.compile(r"^var\(\s*--([\w-]+)\s*(?:,[^)]*)?\)$")
FUNCTION_RE = re.compile(r"^([a-z]+)\((.*)\)$", re.IGNORECASE | re.DOTALL)
HEX_RE = re.compile(r"^#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$", re.IGNORECASE)
RAW_COLOUR_RE = re.compile(
    r"#(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{3,4})\b"
    r"|\b(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb|color)\(",
    re.IGNORECASE,
)
NAMED_COLOURS = {
    "white": (1.0, 1.0, 1.0, 1.0),
    "black": (0.0, 0.0, 0.0, 1.0),
    "transparent": (0.0, 0.0, 0.0, 0.0),
}


class Declaration(NamedTuple):
    chain: tuple[str, ...]
    name: str
    value: str
    line: int


class Colour(NamedTuple):
    """sRGB channels, gamma-encoded, 0 to 1."""

    red: float
    green: float
    blue: float
    alpha: float


class Theme(NamedTuple):
    name: ThemeName
    tokens: dict[str, str]


def main() -> int:
    try:
        config = load()
        theme_flag, arguments = split_theme_flag(sys.argv[1:])
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    themes = configured_themes(config, theme_flag)
    paths = [Path(arg).resolve() for arg in arguments]
    if not paths and config.design is None:
        print("no `design` in the config and no files given; nothing to check")
        return 0
    paths = paths or default_paths(config)
    problems = [problem for path in paths for problem in check_file(path, config, themes)]
    for problem in problems:
        print(problem)
    if not problems:
        print(f"ok: {len(paths)} file(s)")
    return 1 if any(not problem.startswith("skip") for problem in problems) else 0


def default_paths(config: Config) -> list[Path]:
    assert config.design is not None
    completed = subprocess.run(
        ["git", "ls-files", "--", "*.css"],
        cwd=config.root,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked = [config.root / line for line in completed.stdout.splitlines()]
    others = [
        path for path in tracked if path != config.design.tokens and not is_spec_file(path, config)
    ]
    return [config.design.tokens, *others]


def check_file(path: Path, config: Config, themes: tuple[ThemeName, ...]) -> list[str]:
    """Problems in one CSS file, each a line naming the file; `skip` lines aren't failures."""
    declarations = parse_declarations(path.read_text())
    shown_path = relative(path, config.root)
    design = config.design
    if design is None or path == design.tokens or is_spec_file(path, config):
        configured = design.contrast if design else ()
        problems = contrast_problems(declarations, configured, themes)
        return [f"{shown_path}: {problem}" for problem in problems]
    tokens_path = relative(design.tokens, config.root)
    return [
        f"{shown_path}:{declaration.line}: raw colour in `{declaration.name}: {declaration.value}`;"
        f" define it as a token in {tokens_path} and use var(--token)"
        for declaration in declarations
        if RAW_COLOUR_RE.search(declaration.value)
    ]


def is_spec_file(path: Path, config: Config) -> bool:
    return path.is_relative_to(config.specs_dir)


def parse_declarations(css: str) -> list[Declaration]:
    """Every `name: value` in the file with the selectors and at-rules it sits inside."""
    text = re.sub(
        r"/\*.*?\*/", lambda match: "\n" * match.group().count("\n"), css, flags=re.DOTALL
    )
    declarations: list[Declaration] = []
    chain: list[str] = []
    start = 0
    for position, char in enumerate(text):
        if char not in "{};":
            continue
        piece = text[start:position]
        if char == "{":
            chain.append(" ".join(piece.split()))
        elif chain and ":" in piece:
            declarations.append(make_declaration(tuple(chain), piece, text, start))
        if char == "}" and chain:
            chain.pop()
        start = position + 1
    return declarations


def make_declaration(chain: tuple[str, ...], piece: str, text: str, start: int) -> Declaration:
    name, value = piece.split(":", 1)
    leading_space = len(piece) - len(piece.lstrip())
    line = text.count("\n", 0, start + leading_space) + 1
    return Declaration(chain, name.strip(), " ".join(value.split()), line)


def contrast_problems(
    declarations: list[Declaration],
    configured: tuple[ContrastPair, ...],
    theme_names: tuple[ThemeName, ...],
) -> list[str]:
    themes = read_themes(declarations)
    defined = themes[0].tokens
    problems = [
        f"design.contrast names --{name}, which this file doesn't define"
        for name in undefined_names(configured, defined)
    ]
    checkable = [pair for pair in configured if is_defined(pair, defined)]
    pairs = dict.fromkeys([*named_pairs(defined), *checkable])
    for theme in themes:
        if theme.name in theme_names:
            problems += theme_problems(pairs, theme)
    return problems


def theme_problems(pairs: Iterable[ContrastPair], theme: Theme) -> list[str]:
    """One line per failing pair; aliases like Tailwind's `--color-x: var(--x)` report once."""
    problems = []
    checked: set[tuple[str | None, str | None]] = set()
    for pair in pairs:
        colours = (
            resolve_value(pair.foreground, theme.tokens),
            resolve_value(pair.background, theme.tokens),
        )
        if colours in checked:
            continue
        checked.add(colours)
        if problem := check_pair(pair, theme):
            problems.append(problem)
    return problems


def undefined_names(pairs: tuple[ContrastPair, ...], defined: dict[str, str]) -> list[str]:
    names = dict.fromkeys(name for pair in pairs for name in (pair.foreground, pair.background))
    return [name for name in names if name not in defined]


def is_defined(pair: ContrastPair, defined: dict[str, str]) -> bool:
    return pair.foreground in defined and pair.background in defined


def read_themes(declarations: list[Declaration]) -> list[Theme]:
    light: dict[str, str] = {}
    dark: dict[str, str] = {}
    for declaration in declarations:
        is_token = declaration.name.startswith("--")
        if not is_token or not any(THEME_ROOT_RE.search(part) for part in declaration.chain):
            continue
        is_dark = any("dark" in part.lower() for part in declaration.chain)
        (dark if is_dark else light)[declaration.name.removeprefix("--")] = declaration.value
    return [Theme("light", light), Theme("dark", {**light, **dark})]


def named_pairs(tokens: dict[str, str]) -> Iterator[ContrastPair]:
    if "foreground" in tokens and "background" in tokens:
        yield ContrastPair("foreground", "background", TEXT_CONTRAST)
    # Tokens that only alias another, like `--color-muted: var(--muted)`, go last, so a failing
    # pair is reported under the name it was defined with.
    for name in sorted(tokens, key=lambda name: VAR_RE.match(tokens[name]) is not None):
        base = name.removesuffix("-foreground")
        if base != name and base in tokens:
            yield ContrastPair(name, base, TEXT_CONTRAST)
        base = name.removesuffix("-bg")
        if base != name and base in tokens:
            yield ContrastPair(base, name, TEXT_CONTRAST)


def check_pair(pair: ContrastPair, theme: Theme) -> str | None:
    foreground = resolve_colour(pair.foreground, theme.tokens)
    background = resolve_colour(pair.background, theme.tokens)
    label = f"{theme.name}: {pair.foreground} on {pair.background}"
    if foreground is None or background is None:
        return f"skip {label}: can't read the colour"
    backdrop = page_backdrop(theme)
    ratio = contrast_ratio(over(foreground, over(background, backdrop)), over(background, backdrop))
    if ratio >= pair.minimum:
        return None
    # Floor, not round: 4.4998:1 fails 4.5 and must not print as 4.50.
    shown_ratio = math.floor(ratio * 100) / 100
    return (
        f"{label} is {shown_ratio:.2f}:1, under {pair.minimum:g}:1; move one of them further apart"
    )


def page_backdrop(theme: Theme) -> Colour:
    background = resolve_colour("background", theme.tokens)
    if background is not None and background.alpha == 1:
        return background
    return NAMED_COLOUR_BACKDROPS[theme.name]


def resolve_colour(token: str, tokens: dict[str, str]) -> Colour | None:
    value = resolve_value(token, tokens)
    return parse_colour(value) if value is not None else None


def resolve_value(token: str, tokens: dict[str, str]) -> str | None:
    """The token's value with `var()` references followed; None when one names nothing."""
    value = tokens.get(token)
    for _ in range(MAX_VAR_DEPTH):
        match = VAR_RE.match(value or "")
        if match is None:
            break
        value = tokens.get(match.group(1))
    return value


def parse_colour(value: str) -> Colour | None:
    value = value.strip().lower()
    if value in NAMED_COLOURS:
        return Colour(*NAMED_COLOURS[value])
    if HEX_RE.match(value):
        return parse_hex(value[1:])
    match = FUNCTION_RE.match(value)
    if match is None:
        return None
    name, arguments = match.groups()
    parser = COLOUR_FUNCTIONS.get(name)
    try:
        return parser(split_arguments(arguments)) if parser else None
    except (ValueError, IndexError):
        return None


def parse_hex(digits: str) -> Colour:
    if len(digits) in (3, 4):
        digits = "".join(digit * 2 for digit in digits)
    red, green, blue, *alpha = (
        int(digits[index : index + 2], 16) / 255 for index in range(0, len(digits), 2)
    )
    return Colour(red, green, blue, alpha[0] if alpha else 1.0)


def split_arguments(arguments: str) -> tuple[list[str], float]:
    """Channel words and alpha from `a b c / d` or the legacy `a, b, c, d`."""
    channels_text, _, alpha_text = arguments.replace(",", " ").partition("/")
    words = channels_text.split()
    if not alpha_text and len(words) == 4:
        alpha_text = words.pop()
    return words, number(alpha_text, 1.0) if alpha_text.strip() else 1.0


def number(word: str, percent_scale: float) -> float:
    word = word.strip()
    if word == "none":
        return 0.0
    if word.endswith("%"):
        return float(word[:-1]) / 100 * percent_scale
    return float(word)


def hue_degrees(word: str) -> float:
    for unit, degrees in (("deg", 1.0), ("turn", 360.0), ("grad", 0.9), ("rad", 180 / math.pi)):
        if word.endswith(unit):
            return float(word.removesuffix(unit)) * degrees
    return number(word, 1.0)


def parse_rgb(parsed: tuple[list[str], float]) -> Colour:
    words, alpha = parsed
    red, green, blue = (number(word, 255) / 255 for word in words[:3])
    return Colour(red, green, blue, alpha)


def parse_hsl(parsed: tuple[list[str], float]) -> Colour:
    words, alpha = parsed
    hue = hue_degrees(words[0]) % 360
    saturation, lightness = number(words[1], 1.0), number(words[2], 1.0)
    chroma = (1 - abs(2 * lightness - 1)) * saturation

    def channel(offset: float) -> float:
        k = (offset + hue / 30) % 12
        return lightness - chroma / 2 * max(-1, min(k - 3, 9 - k, 1))

    return Colour(channel(0), channel(8), channel(4), alpha)


def parse_oklch(parsed: tuple[list[str], float]) -> Colour:
    words, alpha = parsed
    chroma = number(words[1], OKLAB_PERCENT_SCALE)
    hue = math.radians(hue_degrees(words[2]))
    return oklab_to_srgb(
        number(words[0], 1.0), chroma * math.cos(hue), chroma * math.sin(hue), alpha
    )


def parse_oklab(parsed: tuple[list[str], float]) -> Colour:
    words, alpha = parsed
    a, b = (number(word, OKLAB_PERCENT_SCALE) for word in words[1:3])
    return oklab_to_srgb(number(words[0], 1.0), a, b, alpha)


def oklab_to_srgb(lightness: float, a: float, b: float, alpha: float) -> Colour:
    long = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    medium = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    short = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    linear = (
        4.0767416621 * long - 3.3077115913 * medium + 0.2309699292 * short,
        -1.2684380046 * long + 2.6097574011 * medium - 0.3413193965 * short,
        -0.0041960863 * long - 0.7034186147 * medium + 1.7076147010 * short,
    )
    red, green, blue = (gamma_encode(min(1.0, max(0.0, channel))) for channel in linear)
    return Colour(red, green, blue, alpha)


def gamma_encode(linear: float) -> float:
    return 12.92 * linear if linear <= 0.0031308 else 1.055 * linear ** (1 / 2.4) - 0.055


def gamma_decode(encoded: float) -> float:
    return encoded / 12.92 if encoded <= 0.04045 else ((encoded + 0.055) / 1.055) ** 2.4


def over(top: Colour, bottom: Colour) -> Colour:
    """`top` painted on an opaque `bottom`, blended the way browsers do: in gamma-encoded sRGB."""
    red, green, blue = (
        top_channel * top.alpha + bottom_channel * (1 - top.alpha)
        for top_channel, bottom_channel in zip(top[:3], bottom[:3], strict=True)
    )
    return Colour(red, green, blue, 1.0)


def contrast_ratio(first: Colour, second: Colour) -> float:
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def luminance(colour: Colour) -> float:
    red, green, blue = (gamma_decode(channel) for channel in colour[:3])
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


COLOUR_FUNCTIONS = {
    "rgb": parse_rgb,
    "rgba": parse_rgb,
    "hsl": parse_hsl,
    "hsla": parse_hsl,
    "oklch": parse_oklch,
    "oklab": parse_oklab,
}
NAMED_COLOUR_BACKDROPS = {
    "light": Colour(*NAMED_COLOURS["white"]),
    "dark": Colour(*NAMED_COLOURS["black"]),
}


if __name__ == "__main__":
    sys.exit(main())
