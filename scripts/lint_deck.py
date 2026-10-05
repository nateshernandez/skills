#!/usr/bin/env python3
"""Lint a deck: its storyline, style, slides, and review findings.

Usage: lint_deck.py PATH [PATH ...]
  PATH is a deck folder (decks/<NNN>-<slug>), or one of its files: storyline.md, style.json,
  slides/<id>.html, reviews/<lens>-r<n>.md; or docs/deck/style.json.
  A deck folder lints every file and checks each slide the storyline names exists, once any do.
  Exit 1 on problems.

What's checked comes from skills/write-deck/references/storyline-format.md,
skills/build-slides/references/layouts.md, and skills/review-deck/references/copy.md.
"""

import math
import re
import sys
from itertools import pairwise
from pathlib import Path

from check_tokens import Colour, parse_colour
from kit_config import project_root, relative
from kit_deck import (
    ASSETS_NAME,
    DECK_ID_RE,
    HEADING_DEFAULT_PX,
    HOUSE_STYLE_PATH,
    LAYOUTS,
    REVIEWS_NAME,
    SLIDE_ID_RE,
    SLIDES_NAME,
    STORYLINE_NAME,
    STYLE_NAME,
    TEXT_DEFAULT_PX,
    TEXT_TAGS,
    DeckError,
    Element,
    Kind,
    SlidePlan,
    Storyline,
    Style,
    deck_kind,
    load_storyline,
    load_style,
    normalized,
    parse_html,
    read_json,
    slide_paths,
    style_path,
    style_problems,
    title_element,
    word_cap,
)
from lint_outputs import lint_findings
from lint_spec import parse_fields, split_frontmatter

STORYLINE_SECTIONS = ("Decide", "Slides", "Not saying", "Sources", "Looks like")
REQUIRED_STORYLINE_SECTIONS = ("Slides", "Not saying", "Sources")
STATUSES = ("draft", "approved")
REVIEW_LENSES = ("story", "design", "copy")
MAX_LABEL_WORDS = 25
MAX_SHOWS_WORDS = 20
MAX_DECISIONS = 5
MAX_NOT_SAYING = 6
MAX_SLIDES = 40
SLIDES_PER_MINUTE = 1.5
MAX_SAME_LAYOUT_RUN = 3
POINTS_SHARE = 4
MIN_CLAIM_WORDS = 4
MAX_ELEMENTS = 200
MAX_NOTES_CHARS = 4000
MAX_LIST_ITEMS = {"presented": 4, "read": 6}
MAX_TITLE_DASHES = 0
MAX_BODY_DASHES = 1
MIN_TITLE_CASE_WORDS = 3
TITLE_CASE_SHARE = 0.6

DECISION_RE = re.compile(r"^- \*\*D\d+ [^*]+\*\* → \S")
ALT_RE = re.compile(r"^\s+- _Alt:_\s*\S")
BULLET_RE = re.compile(r"^- \S")
IMAGE_RE = re.compile(r"^!\[[^\]]+\]\((?P<image_path>[^)\s]+)\)$")
REVIEW_NAME_RE = re.compile(r"^(?P<lens>[a-z]+)-r(?P<round>\d+)\.md$")
FINDING_REF_RE = re.compile(r"^- \*\*\[(?:blocker|note)\] (?P<ref>[^*]+)\*\*")
FINDING_REF_SHAPE_RE = re.compile(r"^(?:S\d+(?:, S\d+)*|deck)$")
WORD_RE = re.compile(r"[^\W_][\w'\u2019%.,-]*")
PX_RE = re.compile(r"^(?P<number>\d+(?:\.\d+)?)(?P<unit>px|pt)?$")
COLOR_TOKEN_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|(?:rgba?|hsla?)\([^)]*\)")
COLOR_PROPERTIES = ("color", "background", "background-color", "border")
UNSUPPORTED_VALUE_RE = re.compile(r"var\(|\d(?:em|rem|vw|vh)\b|!important")
UNSUPPORTED_PROPERTIES = frozenset(("z-index", "float", "font"))
UNSUPPORTED_TAGS = frozenset(("style", "script", "iframe", "canvas", "x-embed", "link"))
EMOJI_RE = re.compile("[\U0001f300-\U0001faff☀-➿⭐⬆↔-⇿]")
TITLE_TRIAD_RE = re.compile(r"\b[\w-]+, [\w-]+,? and [\w-]+\b")
NOT_X_BUT_Y_RES = (
    re.compile(
        r"\b(?:it'?s|this is|that'?s|we'?re|this isn'?t|it isn'?t) not\b[^.;!?]{1,60}"
        r"[,;.—\u2013]\s*(?:it'?s|this is|that'?s|we'?re|but)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bnot (?:just|only|merely)\b[^.;!?]{1,60}\bbut\b", re.IGNORECASE),
)
# skills/review-deck/references/copy.md says why each one reads as generated.
BANNED_PHRASES = (
    *("delve", "unlock", "unleash", "seamless", "seamlessly", "leverage", "leveraging"),
    *("robust", "cutting-edge", "game-changer", "game-changing", "revolutionize"),
    *("revolutionary", "transformative", "synergy", "synergies", "holistic", "empower"),
    *("empowering", "elevate", "landscape", "journey", "tapestry", "realm", "paradigm"),
    *("supercharge", "next-level", "world-class", "best-in-class", "innovative", "harness"),
    *("foster", "streamline", "testament", "pivotal", "crucial", "embark", "vibrant"),
    *("meticulous", "ever-evolving", "fast-paced", "in today's", "the power of"),
    *("at the end of the day", "let's dive", "dive into", "deep dive", "key takeaways"),
    *("in conclusion", "furthermore", "moreover", "it's worth noting", "worth noting"),
    *("the magic", "secret sauce", "here's the thing", "the future of"),
)


def main() -> int:
    if not sys.argv[1:]:
        print(__doc__, file=sys.stderr)
        return 1
    root = project_root()
    any_failed = False
    for path in map(Path, sys.argv[1:]):
        problems = lint(path.resolve(), root)
        label = relative(path.resolve(), root)
        print(format_report(label, problems) if problems else f"{label}: ok")
        any_failed |= bool(problems)
    return 1 if any_failed else 0


def format_report(label: str, problems: list[str]) -> str:
    return "\n".join([f"{label}: {len(problems)} problem(s)", *(f"  - {p}" for p in problems)])


def is_deck_file(path: Path, root: Path) -> bool:
    if path == root / HOUSE_STYLE_PATH:
        return True
    deck_dir = find_deck_dir(path)
    if deck_dir is None or deck_dir.parent != root / "decks":
        return False
    inside = path.relative_to(deck_dir).parts
    return (
        inside in ((STORYLINE_NAME,), (STYLE_NAME,))
        or (len(inside) == 2 and inside[0] == SLIDES_NAME and path.suffix == ".html")
        or (len(inside) == 2 and inside[0] == REVIEWS_NAME and path.suffix == ".md")
    )


def find_deck_dir(path: Path) -> Path | None:
    return next((p for p in (path, *path.parents) if DECK_ID_RE.fullmatch(p.name)), None)


def lint(path: Path, root: Path) -> list[str]:
    try:
        return lint_target(path, root)
    except DeckError as error:
        return [str(error)]


def lint_target(path: Path, root: Path) -> list[str]:
    if path.name == STYLE_NAME:
        return style_problems(read_json(path))
    deck_dir = find_deck_dir(path)
    if deck_dir is None:
        message = f"{path} isn't in a decks/<NNN>-<slug> folder"
        raise DeckError(message)
    if path.parent.name == REVIEWS_NAME:
        return lint_review(path, load_storyline(deck_dir))
    storyline = load_storyline(deck_dir)
    style = load_style(style_path(deck_dir, root))
    if path.name == STORYLINE_NAME:
        return lint_storyline(storyline, deck_dir, style)
    if path.suffix == ".html":
        return lint_slide(path, storyline, style, deck_dir)
    return lint_deck_dir(deck_dir, storyline, style)


def lint_deck_dir(deck_dir: Path, storyline: Storyline, style: Style) -> list[str]:
    problems = [f"storyline: {p}" for p in lint_storyline(storyline, deck_dir, style)]
    paths = slide_paths(deck_dir)
    for slide_path in paths:
        problems += [
            f"{slide_path.stem}: {p}" for p in lint_slide(slide_path, storyline, style, deck_dir)
        ]
    if paths:
        built = {slide_path.stem for slide_path in paths}
        problems += [
            f"S{slide.number}: slides/{slide.slide_id}.html is missing"
            for slide in storyline.slides
            if slide.slide_id not in built
        ]
    for review_path in sorted((deck_dir / REVIEWS_NAME).glob("*.md")):
        problems += [f"{review_path.name}: {p}" for p in lint_review(review_path, storyline)]
    return problems


# Storyline


def lint_storyline(storyline: Storyline, deck_dir: Path, style: Style) -> list[str]:
    kind = deck_kind(storyline, style)
    sections = storyline.sections
    return [
        *lint_storyline_fields(storyline, deck_dir.name, kind),
        *lint_storyline_head(storyline, list(sections)),
        *lint_decisions(sections.get("Decide", [])),
        *lint_slide_plans(storyline, style),
        *lint_bullets("Not saying", sections.get("Not saying", []), MAX_NOT_SAYING),
        *lint_bullets("Sources", sections.get("Sources", []), None),
        *lint_images(sections.get("Looks like", []), deck_dir),
    ]


def lint_storyline_fields(storyline: Storyline, folder_name: str, kind: Kind) -> list[str]:
    fields = storyline.fields
    problems = []
    if fields.get("id") != folder_name:
        problems.append(f"frontmatter: id should be `{folder_name}`")
    if fields.get("status") not in STATUSES:
        problems.append(f"frontmatter: status must be one of {list(STATUSES)}")
    if storyline.kind not in ("", "presented", "read"):
        problems.append("frontmatter: kind must be `presented` or `read`")
    if kind == "presented" and not fields.get("minutes", "").isdigit():
        problems.append("frontmatter: a presented deck needs `minutes:`, the talk's length")
    return problems


def lint_storyline_head(storyline: Storyline, headings: list[str]) -> list[str]:
    problems = [] if storyline.title else ["title: first line should be `# <Deck title>`"]
    for label in ("Audience", "Ask"):
        text = storyline.labels.get(label)
        if text is None:
            problems.append(f"{label}: add a `{label}: …` line under the title")
        elif word_count(text) > MAX_LABEL_WORDS:
            problems.append(f"{label}: over {MAX_LABEL_WORDS} words")
    problems += [
        f"sections: unknown `## {name}`" for name in headings if name not in STORYLINE_SECTIONS
    ]
    problems += [
        f"sections: missing `## {name}`"
        for name in REQUIRED_STORYLINE_SECTIONS
        if name not in headings
    ]
    known_order = [name for name in STORYLINE_SECTIONS if name in headings]
    if [name for name in headings if name in STORYLINE_SECTIONS] != known_order:
        problems.append(f"sections: keep the order {list(STORYLINE_SECTIONS)}")
    return problems


def lint_decisions(lines: list[str]) -> list[str]:
    if [line.strip() for line in lines] == ["none"]:
        return []
    heads = [line for line in lines if not line.startswith((" ", "\t"))]
    problems = [
        f"Decide: `{line[:40]}` should be `- **D1 <situation>** → <default>`"
        for line in heads
        if not DECISION_RE.match(line)
    ]
    if len(heads) > MAX_DECISIONS:
        problems.append(f"Decide: {len(heads)} decisions (max {MAX_DECISIONS})")
    alt_count = sum(1 for line in lines if ALT_RE.match(line))
    if alt_count != len(heads):
        problems.append("Decide: each decision needs exactly one `  - _Alt:_` line")
    return problems


def lint_slide_plans(storyline: Storyline, style: Style) -> list[str]:
    slides = storyline.slides
    problems = [
        f"Slides: `{line[:40]}` should be `- **S1 <id> · <layout>** → <title>`"
        for line in storyline.unparsed_slide_lines
    ]
    if not slides:
        return [*problems, "Slides: none yet"]
    problems += lint_slide_ids(slides)
    if slides[0].layout != "title":
        problems.append("Slides: the first slide's layout should be `title`")
    for slide in slides:
        problems += [f"S{slide.number}: {p}" for p in lint_slide_plan(slide, style)]
    problems += lint_slide_counts(slides, storyline.fields.get("minutes", ""))
    problems += lint_layout_runs(slides)
    return problems


def lint_slide_ids(slides: list[SlidePlan]) -> list[str]:
    problems = []
    numbers = [slide.number for slide in slides]
    slide_ids = [slide.slide_id for slide in slides]
    problems += [
        f"Slides: S{n} is used twice" for n in sorted({n for n in numbers if numbers.count(n) > 1})
    ]
    problems += [
        f"Slides: id `{i}` is used twice"
        for i in sorted({i for i in slide_ids if slide_ids.count(i) > 1})
    ]
    problems += [
        f"Slides: id `{i}` must match [A-Za-z0-9_-]"
        for i in slide_ids
        if not SLIDE_ID_RE.fullmatch(i)
    ]
    return problems


def lint_slide_plan(slide: SlidePlan, style: Style) -> list[str]:
    layout = LAYOUTS.get(slide.layout)
    if layout is None:
        return [f"layout `{slide.layout}` isn't one of {list(LAYOUTS)}"]
    problems = lint_title(slide.title, slide.layout, style)
    if layout.is_claim and slide.shows is None:
        problems.append("add `  - _Shows:_ <the evidence on the slide>`")
    if slide.shows and word_count(slide.shows) > MAX_SHOWS_WORDS:
        problems.append(f"Shows: over {MAX_SHOWS_WORDS} words")
    return problems


def lint_slide_counts(slides: list[SlidePlan], minutes: str) -> list[str]:
    problems = []
    if len(slides) > MAX_SLIDES:
        problems.append(f"Slides: {len(slides)} slides (max {MAX_SLIDES}); split the deck")
    content = [
        slide for slide in slides if slide.layout in LAYOUTS and not LAYOUTS[slide.layout].is_frame
    ]
    if minutes.isdigit():
        most = math.ceil(int(minutes) * SLIDES_PER_MINUTE)
        if len(content) > most:
            problems.append(
                f"Slides: {len(content)} content slides for {minutes} minutes "
                f"(max {most}); cut or merge"
            )
    points = sum(1 for slide in content if slide.layout == "points")
    most_points = max(1, len(content) // POINTS_SHARE)
    if points > most_points:
        problems.append(
            f"Slides: {points} `points` slides (max {most_points}); show evidence instead"
        )
    return problems


def lint_layout_runs(slides: list[SlidePlan]) -> list[str]:
    problems = []
    run = 1
    for previous, current in pairwise(slides):
        run = run + 1 if current.layout == previous.layout else 1
        if run == MAX_SAME_LAYOUT_RUN + 1:
            problems.append(
                f"S{current.number}: {run} `{current.layout}` slides in a row; vary the layouts"
            )
    return problems


def lint_bullets(section_name: str, lines: list[str], most: int | None) -> list[str]:
    if not lines:
        return []
    if [line.strip() for line in lines] == ["none"]:
        return []
    problems = [
        f"{section_name}: `{line[:40]}` should be a `- ` bullet"
        for line in lines
        if not BULLET_RE.match(line)
    ]
    if most is not None and len(lines) > most:
        problems.append(f"{section_name}: {len(lines)} bullets (max {most})")
    return problems


def lint_images(lines: list[str], deck_dir: Path) -> list[str]:
    problems = []
    for line in lines:
        image_match = IMAGE_RE.match(line)
        if not image_match:
            problems.append(f"Looks like: `{line[:40]}` should be `![caption](screens/x.png)`")
        elif not (deck_dir / image_match.group("image_path")).exists():
            problems.append(
                f"Looks like: {image_match.group('image_path')} doesn't exist; run render_deck.py"
            )
    return problems


# Titles and copy


def lint_title(title: str, layout_name: str, style: Style) -> list[str]:
    problems = []
    words = word_count(title)
    if words > style.title_max_words:
        problems.append(f"title: {words} words (max {style.title_max_words}); cut to the claim")
    if LAYOUTS[layout_name].is_claim and words < MIN_CLAIM_WORDS:
        problems.append("title: a topic label; write the claim this slide proves as a sentence")
    if title.rstrip().endswith("?"):
        problems.append("title: a question; state the answer")
    if title.count("—") + title.count("\u2013") > MAX_TITLE_DASHES:
        problems.append("title: has a dash; make it one plain sentence")
    if TITLE_TRIAD_RE.search(title):
        problems.append("title: a list of three; name the one that matters")
    problems += lint_title_case(title, style)
    problems += [f"title: {p}" for p in copy_problems(title, style)]
    return problems


def lint_title_case(title: str, style: Style) -> list[str]:
    words = [
        word
        for word in re.findall(r"[A-Za-z][\w'-]*", title)[1:]
        if len(word) >= 4 and not word.isupper()
    ]
    if len(words) < MIN_TITLE_CASE_WORDS:
        return []
    capital_share = sum(word[0].isupper() for word in words) / len(words)
    if style.title_case == "sentence" and capital_share > TITLE_CASE_SHARE:
        return ["title: Title Case; the style wants sentence case"]
    if style.title_case == "title" and capital_share < TITLE_CASE_SHARE:
        return ["title: sentence case; the style wants Title Case"]
    return []


def copy_problems(text: str, style: Style) -> list[str]:
    lowered = text.lower().replace("\u2019", "'")
    problems = [
        f"`{phrase}` reads as generated; say the specific thing"
        for phrase in (*BANNED_PHRASES, *style.banned)
        if re.search(rf"(?<![\w-]){re.escape(phrase.lower())}(?![\w-])", lowered)
    ]
    if any(pattern.search(text) for pattern in NOT_X_BUT_Y_RES):
        problems.append("`not X, but Y` framing; say what it is")
    if EMOJI_RE.search(text):
        problems.append("emoji; use words, or an <x-icon> with its word beside it")
    if "!" in text:
        problems.append("exclamation mark; let the evidence carry the energy")
    return problems


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


# Slides


def lint_slide(path: Path, storyline: Storyline, style: Style, deck_dir: Path) -> list[str]:
    root = parse_html(path.read_text())
    sections = [child for child in root.children if isinstance(child, Element)]
    stray_text = any(isinstance(child, str) and child.strip() for child in root.children)
    if len(sections) != 1 or sections[0].tag != "section" or stray_text:
        return ["file: must hold exactly one <section> and nothing else"]
    section = sections[0]
    if section.attrs.get("id") != path.stem:
        return [f"section: id should be `{path.stem}`, the file name"]
    plan = storyline.plan(path.stem)
    if plan is None or plan.layout not in LAYOUTS:
        return ["storyline: no slide with this id; add it to storyline.md's Slides first"]
    kind = deck_kind(storyline, style)
    return [
        *lint_section_frame(section, plan, kind),
        *lint_supported(section),
        *lint_text_amount(section, plan, kind),
        *lint_lists(section, kind),
        *lint_media(section, plan, deck_dir),
        *lint_palette(section, style),
        *lint_type(section, style),
        *lint_slide_copy(section, style),
    ]


def lint_section_frame(section: Element, plan: SlidePlan, kind: Kind) -> list[str]:
    problems = []
    if "background" not in section.style and "background-color" not in section.style:
        problems.append("section: set `background` on every slide")
    heading = title_element(section)
    if heading is None:
        problems.append(f"title: add the storyline's title as an <h1> or <h2>: `{plan.title}`")
    elif normalized(heading.text()) != normalized(plan.title):
        problems.append(
            f"title: `{heading.text()[:60]}` differs from the storyline's S{plan.number}; "
            "change storyline.md first"
        )
    children = [child for child in section.children if isinstance(child, Element)]
    asides = [child for child in children if child.tag == "aside"]
    if (asides and children[-1].tag != "aside") or len(asides) > 1:
        problems.append("notes: one <aside>, the section's last child")
    if kind == "presented" and not (asides and asides[0].text()):
        problems.append(
            "notes: a presented deck needs speaker notes in an <aside>: what you'll say"
        )
    if asides and len(asides[0].text()) > MAX_NOTES_CHARS:
        problems.append(f"notes: over {MAX_NOTES_CHARS} characters")
    return problems


def lint_supported(section: Element) -> list[str]:
    problems = []
    elements = section.elements()
    if len(elements) > MAX_ELEMENTS:
        problems.append(f"elements: {len(elements)} (max {MAX_ELEMENTS}); split the slide")
    for element in elements:
        where = f"line {element.line} <{element.tag}>"
        if element.tag in UNSUPPORTED_TAGS:
            problems.append(f"{where}: not in the slide format")
        if "class" in element.attrs or any(name.startswith("on") for name in element.attrs):
            problems.append(f"{where}: classes and handlers are dropped; use inline style")
        for name, value in element.style.items():
            if (
                name in UNSUPPORTED_PROPERTIES
                or name.startswith("margin")
                or UNSUPPORTED_VALUE_RE.search(value)
            ):
                problems.append(f"{where}: `{name}: {value}` is outside the slide format")
    return list(dict.fromkeys(problems))


def lint_text_amount(section: Element, plan: SlidePlan, kind: Kind) -> list[str]:
    heading = title_element(section)
    body_text = " ".join(
        element.text(frozenset(("svg", "aside")))
        for element in section.children
        if isinstance(element, Element)
        and element is not heading
        and element.tag not in ("aside", "svg")
    )
    cap = word_cap(LAYOUTS[plan.layout], kind)
    words = word_count(body_text)
    if words > cap:
        return [
            f"body: {words} words (max {cap} on a `{plan.layout}` slide); "
            "move the rest to the notes, or split the slide"
        ]
    return []


def lint_lists(section: Element, kind: Kind) -> list[str]:
    problems = []
    for element in section.elements():
        if element.tag not in ("ul", "ol"):
            continue
        items = [
            child for child in element.children if isinstance(child, Element) and child.tag == "li"
        ]
        if len(items) > MAX_LIST_ITEMS[kind]:
            problems.append(
                f"line {element.line}: {len(items)} list items (max {MAX_LIST_ITEMS[kind]})"
            )
        if any(inner.tag in ("ul", "ol") for item in items for inner in item.elements()[1:]):
            problems.append(f"line {element.line}: nested list; make it two slides or a table")
    for element in section.elements():
        first = next(
            (
                child
                for child in element.children
                if not (isinstance(child, str) and not child.strip())
            ),
            None,
        )
        is_label = (
            isinstance(first, Element)
            and first.tag in ("b", "strong")
            and first.text().endswith(":")
        )
        if element.tag in ("li", "p") and is_label:
            problems.append(
                f"line {element.line}: a `Label:` lead-in; write the point as a sentence"
            )
    return problems


def lint_media(section: Element, plan: SlidePlan, deck_dir: Path) -> list[str]:
    problems = []
    tags = {element.tag for element in section.elements()}
    needs = LAYOUTS[plan.layout].needs
    if needs and not tags & set(needs):
        problems.append(
            f"layout: a `{plan.layout}` slide needs one of {['<' + tag + '>' for tag in needs]}"
        )
    for element in section.elements():
        if element.tag == "img":
            problems += lint_image(element, deck_dir)
        if element.tag == "svg" and any(inner.tag == "text" for inner in element.elements()):
            problems.append(
                f"line {element.line}: <text> in an <svg> gets no fonts; put labels in <p>s over it"
            )
        if element.tag == "svg" and "aria-label" not in element.attrs:
            problems.append(f"line {element.line}: <svg> needs aria-label, its alt text")
    return problems


def lint_image(image: Element, deck_dir: Path) -> list[str]:
    src = image.attrs.get("src", "")
    problems = [] if "alt" in image.attrs else [f"line {image.line}: <img> needs alt"]
    if not src.startswith(f"{ASSETS_NAME}/"):
        problems.append(f"line {image.line}: src `{src[:40]}` should be a file in {ASSETS_NAME}/")
    elif not (deck_dir / src).is_file():
        problems.append(f"line {image.line}: {src} doesn't exist")
    return problems


def lint_palette(section: Element, style: Style) -> list[str]:
    palette = {rounded(colour) for colour in style.palette}
    problems = []
    for element in section.elements():
        for name, value in element.style.items():
            if not name.startswith(COLOR_PROPERTIES):
                continue
            for token in COLOR_TOKEN_RE.findall(value):
                colour = parse_colour(token)
                is_opaque = colour is not None and colour.alpha == 1
                if is_opaque and rounded(colour) not in palette:
                    problems.append(f"line {element.line}: `{token}` isn't in the style's colors")
    return list(dict.fromkeys(problems))


def rounded(colour: Colour | None) -> tuple[int, ...]:
    assert colour is not None
    return tuple(round(channel * 255) for channel in colour[:3])


def lint_type(section: Element, style: Style) -> list[str]:
    sizes = set(style.sizes.values())
    problems = []
    for element, px in text_sizes(section, None):
        if px is not None and px not in sizes:
            problems.append(
                f"line {element.line} <{element.tag}>: {px:g}px isn't one of the style's sizes "
                f"{sorted(sizes)}"
            )
    for element in section.elements():
        family = element.style.get("font-family")
        first = family.split(",")[0].strip().strip("'\"") if family else None
        if first is not None and first not in style.families:
            problems.append(f"line {element.line}: font `{first}` isn't in the style's fonts")
    return list(dict.fromkeys(problems))


def text_sizes(element: Element, inherited_px: float | None) -> list[tuple[Element, float | None]]:
    own_px = font_px(element.style.get("font-size"))
    if element.tag in HEADING_DEFAULT_PX:
        px: float | None = own_px or HEADING_DEFAULT_PX[element.tag]
    else:
        px = own_px or inherited_px or (TEXT_DEFAULT_PX if element.tag in TEXT_TAGS else None)
    found = [(element, px)] if element.tag in TEXT_TAGS else []
    for child in element.children:
        if isinstance(child, Element) and child.tag not in ("svg", "aside"):
            found += text_sizes(child, px)
    return found


def font_px(value: str | None) -> float | None:
    size_match = PX_RE.match(value or "")
    if size_match is None:
        return None
    number = float(size_match.group("number"))
    return number * 2 if size_match.group("unit") == "pt" else number


def lint_slide_copy(section: Element, style: Style) -> list[str]:
    heading = title_element(section)
    body = " ".join(
        child.text(frozenset(("svg", "aside")))
        for child in section.children
        if isinstance(child, Element) and child is not heading and child.tag != "aside"
    )
    notes = " ".join(
        child.text()
        for child in section.children
        if isinstance(child, Element) and child.tag == "aside"
    )
    problems = [f"body: {p}" for p in copy_problems(body, style)]
    if body.count("—") > MAX_BODY_DASHES:
        problems.append(f"body: {body.count('—')} em dashes; use periods")
    problems += [f"notes: {p}" for p in copy_problems(notes, style) if "exclamation" not in p]
    return problems


# Reviews


def lint_review(path: Path, storyline: Storyline) -> list[str]:
    frontmatter, body = split_frontmatter(path.read_text())
    if frontmatter is None:
        return ["frontmatter: missing `---` block with lens, round, verdict"]
    fields = parse_fields(frontmatter)
    lens = fields.get("lens", "")
    problems = []
    if lens not in REVIEW_LENSES:
        problems.append(f"frontmatter: lens must be one of {list(REVIEW_LENSES)}")
    if path.name != f"{lens}-r{fields.get('round')}.md" or not REVIEW_NAME_RE.match(path.name):
        problems.append(f"file name: should be `{lens}-r{fields.get('round', '<round>')}.md`")
    if fields.get("verdict") not in ("pass", "fail"):
        problems.append("frontmatter: verdict must be `pass` or `fail`")
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("# "):
        return [*problems, "title: first line should be `# <Lens> review, round <n>`"]
    finding_lines = lines[1:]
    if [line.strip() for line in finding_lines] == ["none"]:
        return problems + (
            ["verdict: no findings means `verdict: pass`"]
            if fields.get("verdict") == "fail"
            else []
        )
    finding_problems, blocker_count = lint_findings(finding_lines)
    problems += [p.replace("1.B2 · file:line", "S3") for p in finding_problems]
    problems += lint_finding_refs(finding_lines, storyline)
    expected_verdict = "fail" if blocker_count else "pass"
    if fields.get("verdict") != expected_verdict:
        problems.append(f"verdict: {blocker_count} blocker(s) means `verdict: {expected_verdict}`")
    return problems


def lint_finding_refs(finding_lines: list[str], storyline: Storyline) -> list[str]:
    numbers = {f"S{slide.number}" for slide in storyline.slides}
    problems = []
    for line in finding_lines:
        ref_match = FINDING_REF_RE.match(line)
        if ref_match is None:
            continue
        ref = ref_match.group("ref").strip()
        if not FINDING_REF_SHAPE_RE.match(ref):
            problems.append(f"findings: ref `{ref}` should be a slide like `S3`, or `deck`")
        problems += [
            f"findings: {s} isn't in the storyline"
            for s in ref.split(", ")
            if s.startswith("S") and s not in numbers
        ]
    return problems


if __name__ == "__main__":
    sys.exit(main())
