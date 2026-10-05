"""Read a deck's files: its style, storyline, and slides. Imported by the deck scripts.

A deck lives in decks/<NNN>-<slug>/: storyline.md (the contract), slides/<id>.html (one
Slides-format <section> each), assets/, screens/, reviews/, and published.json. Its style is
the deck's own style.json, else the project's docs/deck/style.json.
skills/write-deck/references/storyline-format.md and skills/define-deck-style/references/
style-format.md describe the files.
"""

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Literal, NamedTuple, get_args

from check_tokens import Colour, parse_colour
from lint_spec import parse_fields, split_frontmatter

DECKS_PATH = Path("decks")
HOUSE_STYLE_PATH = Path("docs") / "deck" / "style.json"
STYLE_NAME = "style.json"
STORYLINE_NAME = "storyline.md"
SLIDES_NAME = "slides"
ASSETS_NAME = "assets"
SCREENS_NAME = "screens"
REVIEWS_NAME = "reviews"
PUBLISHED_NAME = "published.json"
DECK_ID_RE = re.compile(r"(?P<number>\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*")
SLIDE_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")

Kind = Literal["presented", "read"]
KINDS: tuple[Kind, ...] = get_args(Kind)
TitleCase = Literal["sentence", "title", "any"]
TITLE_CASES: tuple[TitleCase, ...] = get_args(TitleCase)
# A read deck carries its own explanation, so its slides may hold this many times the words.
READ_WORDS_FACTOR = 2.5
CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 1080
MIN_FONT_PX = 24
HEADING_DEFAULT_PX = {"h1": 96, "h2": 64, "h3": 44}
TEXT_DEFAULT_PX = 32


class Layout(NamedTuple):
    body_words: int
    needs: tuple[str, ...]
    is_claim: bool
    fills: bool
    is_frame: bool


def _content(body_words: int, needs: tuple[str, ...] = (), *, fills: bool) -> Layout:
    return Layout(body_words, needs, is_claim=True, fills=fills, is_frame=False)


def _frame(body_words: int) -> Layout:
    return Layout(body_words, (), is_claim=False, fills=False, is_frame=True)


# skills/build-slides/references/layouts.md explains when each one fits.
LAYOUTS: dict[str, Layout] = {
    "title": _frame(20),
    "section": _frame(12),
    "statement": _content(20, fills=False),
    "big-number": _content(20, fills=False),
    "chart": _content(25, fills=True),
    "diagram": _content(30, fills=True),
    "comparison": _content(45, fills=True),
    "table": _content(60, ("table",), fills=True),
    "image": _content(15, ("img",), fills=False),
    "quote": _content(45, fills=False),
    "points": _content(30, fills=True),
    "timeline": _content(40, fills=True),
    "closing": _frame(25),
}


class DeckError(Exception):
    """A deck file is missing or malformed; the message names the file and the fix."""


# Style


REQUIRED_COLORS = ("background", "text", "muted", "accent")
REQUIRED_SIZES = ("title", "body", "small")
REQUIRED_FONTS = ("heading", "body")
STYLE_FIELDS = frozenset(("kind", "fonts", "colors", "sizes", "titles", "banned"))
MAX_SIZES = 5
MAX_FAMILIES = 3
DEFAULT_TITLE_MAX_WORDS = 15
GOOGLE_FONTS_PREFIX = "https://fonts.googleapis.com/css2?"
HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}")


class Face(NamedTuple):
    family: str
    href: str | None


class Style(NamedTuple):
    kind: Kind
    fonts: dict[str, Face]
    colors: dict[str, str]
    sizes: dict[str, int]
    title_case: TitleCase
    title_max_words: int
    banned: tuple[str, ...]

    @property
    def families(self) -> frozenset[str]:
        return frozenset(face.family for face in self.fonts.values())

    @property
    def palette(self) -> frozenset[Colour]:
        return frozenset(filter(None, map(parse_colour, self.colors.values())))

    def size(self, role: str) -> int:
        return self.sizes.get(role, self.sizes["title"])


def style_path(deck_dir: Path, root: Path) -> Path:
    deck_style = deck_dir / STYLE_NAME
    if deck_style.exists():
        return deck_style
    house_style = root / HOUSE_STYLE_PATH
    if house_style.exists():
        return house_style
    message = f"no {deck_style} or {HOUSE_STYLE_PATH}; run /kit:define-deck-style or write one"
    raise DeckError(message)


def load_style(path: Path) -> Style:
    raw = read_json(path)
    problems = style_problems(raw)
    if problems:
        raise DeckError(f"{path}: " + "; ".join(problems))
    assert isinstance(raw, dict)
    return parse_style(raw)


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as error:
        message = f"{path}: invalid JSON at line {error.lineno}: {error.msg}"
        raise DeckError(message) from error


def style_problems(raw: object) -> list[str]:
    if not isinstance(raw, dict):
        return ["style: must be a JSON object"]
    problems = [f"style: unknown field `{name}`" for name in sorted(set(raw) - STYLE_FIELDS)]
    if raw.get("kind", "presented") not in KINDS:
        problems.append(f"kind: must be one of {list(KINDS)}")
    problems += font_problems(raw.get("fonts"))
    problems += color_problems(raw.get("colors"))
    problems += size_problems(raw.get("sizes"))
    problems += title_problems(raw.get("titles", {}))
    banned = raw.get("banned", [])
    if not isinstance(banned, list) or not all(isinstance(phrase, str) for phrase in banned):
        problems.append("banned: must be a list of phrases")
    return problems


def font_problems(fonts: object) -> list[str]:
    if not isinstance(fonts, dict):
        return [f"fonts: must map {list(REQUIRED_FONTS)} to {{family, href}}"]
    problems = [f"fonts: missing `{role}`" for role in REQUIRED_FONTS if role not in fonts]
    families = set()
    for role, face in fonts.items():
        if not isinstance(face, dict) or not isinstance(face.get("family"), str):
            problems.append(f"fonts.{role}: must be {{family, href}}")
            continue
        families.add(face["family"])
        href = face.get("href")
        if href is not None and not str(href).startswith(GOOGLE_FONTS_PREFIX):
            problems.append(f"fonts.{role}.href: only `{GOOGLE_FONTS_PREFIX}…` links load")
    if len(families) > MAX_FAMILIES:
        problems.append(f"fonts: {len(families)} families (max {MAX_FAMILIES})")
    return problems


def color_problems(colors: object) -> list[str]:
    if not isinstance(colors, dict):
        return [f"colors: must map names, including {list(REQUIRED_COLORS)}, to hex"]
    problems = [f"colors: missing `{name}`" for name in REQUIRED_COLORS if name not in colors]
    problems += [
        f"colors.{name}: `{value}` should be `#rrggbb`"
        for name, value in colors.items()
        if not isinstance(value, str) or not HEX_COLOR_RE.fullmatch(value)
    ]
    return problems


def size_problems(sizes: object) -> list[str]:
    if not isinstance(sizes, dict):
        return [f"sizes: must map roles, including {list(REQUIRED_SIZES)}, to px"]
    problems = [f"sizes: missing `{role}`" for role in REQUIRED_SIZES if role not in sizes]
    if len(set(sizes.values())) > MAX_SIZES:
        problems.append(f"sizes: {len(set(sizes.values()))} sizes (max {MAX_SIZES})")
    problems += [
        f"sizes.{role}: {px} should be a whole number of px, at least {MIN_FONT_PX}"
        for role, px in sizes.items()
        if not isinstance(px, int) or px < MIN_FONT_PX
    ]
    return problems


def title_problems(titles: object) -> list[str]:
    if not isinstance(titles, dict):
        return ["titles: must be {case, max_words}"]
    problems = []
    if titles.get("case", "sentence") not in TITLE_CASES:
        problems.append(f"titles.case: must be one of {list(TITLE_CASES)}")
    max_words = titles.get("max_words", DEFAULT_TITLE_MAX_WORDS)
    if not isinstance(max_words, int) or not 4 <= max_words <= 25:
        problems.append("titles.max_words: must be a whole number from 4 to 25")
    return problems


def parse_style(raw: dict) -> Style:
    titles = raw.get("titles", {})
    return Style(
        kind=raw.get("kind", "presented"),
        fonts={role: Face(face["family"], face.get("href")) for role, face in raw["fonts"].items()},
        colors={name: value.lower() for name, value in raw["colors"].items()},
        sizes=dict(raw["sizes"]),
        title_case=titles.get("case", "sentence"),
        title_max_words=titles.get("max_words", DEFAULT_TITLE_MAX_WORDS),
        banned=tuple(raw.get("banned", [])),
    )


def face_key(family: str) -> str:
    return family.lower().replace(" ", "-")


# Storyline


SLIDE_ITEM_RE = re.compile(
    r"^- \*\*S(?P<number>\d+) (?P<slide_id>\S+) · (?P<layout>[a-z-]+)\*\* → (?P<title>\S.*)$"
)
SHOWS_RE = re.compile(r"^\s+- _Shows:_\s*(?P<shows>\S.*)$")
LABEL_RE = re.compile(r"^(?P<label>Audience|Ask): (?P<text>\S.*)$")


class SlidePlan(NamedTuple):
    number: int
    slide_id: str
    layout: str
    title: str
    shows: str | None


class Storyline(NamedTuple):
    fields: dict[str, str]
    title: str
    labels: dict[str, str]
    sections: dict[str, list[str]]
    slides: list[SlidePlan]
    unparsed_slide_lines: list[str]

    @property
    def kind(self) -> str:
        return self.fields.get("kind", "")

    def plan(self, slide_id: str) -> SlidePlan | None:
        return next((slide for slide in self.slides if slide.slide_id == slide_id), None)


def load_storyline(deck_dir: Path) -> Storyline:
    path = deck_dir / STORYLINE_NAME
    if not path.exists():
        message = f"{path} doesn't exist; create the deck with new_deck.py"
        raise DeckError(message)
    return parse_storyline(path.read_text())


def parse_storyline(text: str) -> Storyline:
    frontmatter, body = split_frontmatter(text)
    fields = parse_fields(frontmatter) if frontmatter is not None else {}
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    title = lines[0][2:].strip() if lines and lines[0].startswith("# ") else ""
    labels: dict[str, str] = {}
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in lines[1:] if title else lines:
        if line.startswith("## "):
            current = sections.setdefault(line[3:].strip(), [])
        elif current is not None:
            current.append(line)
        elif label_match := LABEL_RE.match(line):
            labels[label_match.group("label")] = label_match.group("text")
    slides, unparsed = parse_slide_items(sections.get("Slides", []))
    return Storyline(fields, title, labels, sections, slides, unparsed)


def parse_slide_items(lines: list[str]) -> tuple[list[SlidePlan], list[str]]:
    slides: list[SlidePlan] = []
    unparsed: list[str] = []
    for line in lines:
        item_match = SLIDE_ITEM_RE.match(line)
        shows_match = SHOWS_RE.match(line)
        if item_match:
            slides.append(
                SlidePlan(
                    number=int(item_match.group("number")),
                    slide_id=item_match.group("slide_id"),
                    layout=item_match.group("layout"),
                    title=item_match.group("title").strip(),
                    shows=None,
                )
            )
        elif shows_match and slides and slides[-1].shows is None:
            slides[-1] = slides[-1]._replace(shows=shows_match.group("shows").strip())
        else:
            unparsed.append(line)
    return slides, unparsed


def deck_kind(storyline: Storyline, style: Style) -> Kind:
    return "read" if (storyline.kind or style.kind) == "read" else "presented"


def word_cap(layout: Layout, kind: Kind) -> int:
    return round(layout.body_words * (READ_WORDS_FACTOR if kind == "read" else 1))


# Slides


VOID_TAGS = frozenset(("img", "br", "hr", "meta", "link", "input", "source"))
TEXT_TAGS = frozenset(("h1", "h2", "h3", "p", "li", "th", "td"))
STYLE_DECLARATION_RE = re.compile(r"\s*([-\w]+)\s*:\s*((?:[^;(]|\([^)]*\))+)")


@dataclass(frozen=True)
class Element:
    tag: str
    attrs: dict[str, str]
    line: int
    children: list["Element | str"] = field(default_factory=list)

    @property
    def style(self) -> dict[str, str]:
        return parse_inline_style(self.attrs.get("style", ""))

    def elements(self) -> list["Element"]:
        """This element and every element inside it, in document order."""
        found: list[Element] = [self]
        for child in self.children:
            if isinstance(child, Element):
                found += child.elements()
        return found

    def text(self, skip: frozenset[str] = frozenset()) -> str:
        parts = []
        for child in self.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag not in skip:
                parts.append(child.text(skip))
                if child.tag in TEXT_TAGS or child.tag == "br":
                    parts.append(" ")
        return re.sub(r"\s+", " ", "".join(parts)).strip()


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("#root", {}, 0)
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = Element(tag, {name: value or "" for name, value in attrs}, self.getpos()[0])
        self.stack[-1].children.append(element)
        if tag not in VOID_TAGS:
            self.stack.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = Element(tag, {name: value or "" for name, value in attrs}, self.getpos()[0])
        self.stack[-1].children.append(element)

    def handle_endtag(self, tag: str) -> None:
        open_tags = [element.tag for element in self.stack]
        if tag in open_tags[1:]:
            while self.stack[-1].tag != tag:
                self.stack.pop()
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def parse_html(text: str) -> Element:
    builder = _TreeBuilder()
    builder.feed(text)
    builder.close()
    return builder.root


def parse_inline_style(style: str) -> dict[str, str]:
    return {
        name.lower(): value.strip()
        for name, value in STYLE_DECLARATION_RE.findall(style.replace("\n", " "))
    }


def slide_paths(deck_dir: Path) -> list[Path]:
    return sorted((deck_dir / SLIDES_NAME).glob("*.html"))


def title_element(section: Element) -> Element | None:
    return next((element for element in section.elements() if element.tag in ("h1", "h2")), None)


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
