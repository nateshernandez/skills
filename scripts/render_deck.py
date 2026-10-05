#!/usr/bin/env python3
"""Render a deck in headless Chrome: screenshots for people, layout checks for agents.

Usage:
  render_deck.py DECK_DIR               render slides/ to screens/<id>.png and the contact
                                        sheet screens/deck.png; exit 1 on layout problems
  render_deck.py --wireframes DECK_DIR  render the storyline as wireframes, real titles in grey
                                        boxes, to screens/wireframes.png; exit 1 on long titles

Each slide is checked for: content past the 1920x1080 canvas, text wider or taller than its box,
text outside the margins or in the footer band, text overlapping text, type under 24px, text
contrast under 4.5:1 (3:1 at 44px and up), a title wrapping past two lines (three on the
cover), a heading that sits elsewhere than on the deck's other content slides, and a
content slide whose body stops above 60% of the height or floats far below its heading.
Chrome comes from KIT_BROWSER, else the usual install paths, else Playwright's download.
"""

import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

from kit_config import project_root
from kit_deck import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    LAYOUTS,
    SCREENS_NAME,
    DeckError,
    SlidePlan,
    Storyline,
    Style,
    load_storyline,
    load_style,
    slide_paths,
    style_path,
)

SHEET_COLUMNS = 4
SHEET_SCALE = 0.25
SHEET_GAP = 24
SHEET_LABEL = 40
SLIDE_SCALE = 0.5
FILL_SHARE = 0.6
MAX_HEADING_GAP_PX = 240
# Big enough to read on the contact sheet, a quarter of full size.
PLACEHOLDER_PX = 48
HEADING_TOLERANCE_PX = 4
FREE_HEADING_LAYOUTS = ("statement", "quote")
VIRTUAL_TIME_MS = 6000
PARALLEL_SHOTS = 4
CHROME_TIMEOUT_S = 60
BROWSER_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)
BROWSER_COMMANDS = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
PLAYWRIGHT_GLOBS = (
    "Library/Caches/ms-playwright/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium",
    ".cache/ms-playwright/chromium-*/chrome-linux*/chrome",
)
REPORT_RE = re.compile(r'<pre id="kit-report">(?P<report>\[.*?)</pre>', re.DOTALL)
SCRIPT_PATH = Path(__file__).resolve().parent / "render_deck.js"

# The slide format's defaults (the Slides type's format.md), so local renders match its canvas.
CANVAS_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{background:#7f7f7f}
section{position:relative;display:block;width:1920px;height:1080px;overflow:hidden;
  font-size:32px;line-height:1.4}
h1{font-size:96px;font-weight:600;line-height:1.1}
h2{font-size:64px;font-weight:600;line-height:1.15}
h3{font-size:44px;font-weight:600;line-height:1.2}
ul,ol{padding-left:1.2em}
table{border-collapse:collapse}
th,td{border:1px solid currentColor;padding:.35em .6em;text-align:left}
img,svg,x-shape,x-icon{display:block}
aside,x-connector{display:none}
"""


class Rendered(NamedTuple):
    slide_id: str
    title_top: float | None
    title_left: float | None
    title_bottom: float | None
    title_lines: int
    body_bottom: float
    body_top: float | None
    problems: list[str]


def main() -> int:
    arguments = sys.argv[1:]
    is_wireframes = arguments[:1] == ["--wireframes"]
    paths = arguments[1:] if is_wireframes else arguments
    if len(paths) != 1:
        print(__doc__, file=sys.stderr)
        return 1
    deck_dir = Path(paths[0]).resolve()
    try:
        storyline = load_storyline(deck_dir)
        style = load_style(style_path(deck_dir, project_root()))
        browser = find_browser()
    except DeckError as error:
        print(error, file=sys.stderr)
        return 1
    screens_dir = deck_dir / SCREENS_NAME
    screens_dir.mkdir(exist_ok=True)
    if is_wireframes:
        problems = render_wireframes(storyline, style, deck_dir, browser)
    else:
        problems = render_slides(storyline, style, deck_dir, browser)
    for problem in problems:
        print(problem)
    return 1 if problems else 0


def find_browser() -> str:
    candidates = [os.environ.get("KIT_BROWSER", ""), *BROWSER_CANDIDATES]
    candidates += [shutil.which(command) or "" for command in BROWSER_COMMANDS]
    candidates += [str(path) for pattern in PLAYWRIGHT_GLOBS for path in Path.home().glob(pattern)]
    found = next((path for path in candidates if path and Path(path).is_file()), None)
    if found is None:
        message = "no Chrome or Chromium found; install Chrome or set KIT_BROWSER to its binary"
        raise DeckError(message)
    return found


def render_wireframes(
    storyline: Storyline, style: Style, deck_dir: Path, browser: str
) -> list[str]:
    sections = [wireframe(plan, style) for plan in storyline.slides]
    labels = {plan.slide_id: f"S{plan.number} · {plan.layout}" for plan in storyline.slides}
    with tempfile.TemporaryDirectory() as work_dir:
        harness = write_harness(Path(work_dir), deck_dir, style, sections, labels)
        rendered = check(browser, harness)
        shoot_sheet(browser, harness, deck_dir / SCREENS_NAME / "wireframes.png", len(sections))
    print(deck_dir / SCREENS_NAME / "wireframes.png")
    numbers = {plan.slide_id: plan.number for plan in storyline.slides}
    return [
        f"S{numbers[result.slide_id]}: {problem}"
        for result in rendered
        for problem in result.problems
        if problem.startswith("title wraps")
    ]


def render_slides(storyline: Storyline, style: Style, deck_dir: Path, browser: str) -> list[str]:
    paths = slide_paths(deck_dir)
    if not paths:
        message = f"{deck_dir}/slides has no slides yet"
        raise DeckError(message)
    order = {plan.slide_id: index for index, plan in enumerate(storyline.slides)}
    paths.sort(key=lambda path: order.get(path.stem, len(order)))
    sections = [path.read_text() for path in paths]
    labels = {plan.slide_id: f"S{plan.number} · {plan.slide_id}" for plan in storyline.slides}
    screens_dir = deck_dir / SCREENS_NAME
    with tempfile.TemporaryDirectory() as work_dir:
        harness = write_harness(Path(work_dir), deck_dir, style, sections, labels)
        rendered = check(browser, harness)
        shots = [(f"#slide={path.stem}", screens_dir / f"{path.stem}.png") for path in paths]
        shoot_slides(browser, harness, shots)
        shoot_sheet(browser, harness, screens_dir / "deck.png", len(sections))
    print(screens_dir / "deck.png")
    return judge(rendered, storyline)


def judge(rendered: list[Rendered], storyline: Storyline) -> list[str]:
    plans = {plan.slide_id: plan for plan in storyline.slides}
    problems = []
    for result in rendered:
        plan = plans.get(result.slide_id)
        label = f"S{plan.number} {result.slide_id}" if plan else result.slide_id
        slide_problems = list(result.problems)
        if plan and LAYOUTS.get(plan.layout) and LAYOUTS[plan.layout].fills:
            slide_problems += fill_problems(result)
        problems += [f"{label}: {problem}" for problem in slide_problems]
    problems += heading_problems(rendered, plans)
    return problems


def fill_problems(result: Rendered) -> list[str]:
    lowest = CANVAS_HEIGHT * FILL_SHARE
    problems = []
    if result.body_bottom < lowest:
        problems.append(
            f"body stops at y={result.body_bottom:.0f}, above {lowest:.0f}; "
            "give the evidence block flex:1 and let it fill"
        )
    heading_bottom = result.title_bottom
    if result.body_top is not None and heading_bottom is not None:
        gap = result.body_top - heading_bottom
        if gap > MAX_HEADING_GAP_PX:
            problems.append(
                f"{gap:.0f}px of empty space between the heading and the body; "
                "grow the evidence (flex:1, larger type) instead of pushing it down"
            )
    return problems


def heading_problems(rendered: list[Rendered], plans: dict[str, SlidePlan]) -> list[str]:
    """Content slides keep their heading in one place; statements and quotes may center."""
    anchored = [
        result
        for result in rendered
        if (plan := plans.get(result.slide_id))
        and plan.layout in LAYOUTS
        and not LAYOUTS[plan.layout].is_frame
        and plan.layout not in FREE_HEADING_LAYOUTS
        and result.title_top is not None
    ]
    if not anchored:
        return []
    first = anchored[0]
    assert first.title_top is not None and first.title_left is not None
    problems = []
    for result in anchored[1:]:
        assert result.title_top is not None and result.title_left is not None
        moved = max(
            abs(result.title_top - first.title_top), abs(result.title_left - first.title_left)
        )
        if moved > HEADING_TOLERANCE_PX:
            problems.append(
                f"S{plans[result.slide_id].number} {result.slide_id}: heading at "
                f"({result.title_left:.0f}, {result.title_top:.0f}); content slides put it at "
                f"({first.title_left:.0f}, {first.title_top:.0f}), "
                f"like S{plans[first.slide_id].number}"
            )
    return problems


# Harness


def write_harness(
    work_dir: Path, deck_dir: Path, style: Style, sections: list[str], labels: dict[str, str]
) -> Path:
    font_links = "".join(
        f'<link rel="stylesheet" href="{html.escape(face.href)}">'
        for face in {face.href: face for face in style.fonts.values() if face.href}.values()
        if face.href
    )
    settings = {"labels": labels, "scale": SHEET_SCALE, "gap": SHEET_GAP, "label": SHEET_LABEL}
    page = (
        '<!doctype html><html><head><meta charset="utf-8">'
        f'<base href="{deck_dir.as_uri()}/">{font_links}<style>{CANVAS_CSS}</style></head>'
        f'<body><div id="kit-slides">{"".join(sections)}</div>'
        f"<script>const KIT = {json.dumps(settings)};</script>"
        f"<script>{SCRIPT_PATH.read_text()}</script></body></html>"
    )
    harness = work_dir / "deck.html"
    harness.write_text(page)
    return harness


def check(browser: str, harness: Path) -> list[Rendered]:
    output = run_chrome(browser, ["--dump-dom", harness.as_uri() + "#check"])
    report_match = REPORT_RE.search(output)
    if report_match is None:
        message = "the browser returned no layout report; is a slide's HTML malformed?"
        raise DeckError(message)
    return [
        Rendered(
            slide_id=entry["id"],
            title_top=entry["titleTop"],
            title_left=entry["titleLeft"],
            title_bottom=entry["titleBottom"],
            title_lines=entry["titleLines"],
            body_bottom=entry["bodyBottom"],
            body_top=entry["bodyTop"],
            problems=entry["problems"],
        )
        for entry in json.loads(html.unescape(report_match.group("report")))
    ]


def shoot_slides(browser: str, harness: Path, shots: list[tuple[str, Path]]) -> None:
    def shoot(shot: tuple[str, Path]) -> None:
        fragment, out_path = shot
        size = f"--window-size={CANVAS_WIDTH},{CANVAS_HEIGHT}"
        scale = f"--force-device-scale-factor={SLIDE_SCALE}"
        run_chrome(browser, [size, scale, f"--screenshot={out_path}", harness.as_uri() + fragment])

    with ThreadPoolExecutor(max_workers=PARALLEL_SHOTS) as pool:
        list(pool.map(shoot, shots))


def shoot_sheet(browser: str, harness: Path, out_path: Path, slide_count: int) -> None:
    cell_width = CANVAS_WIDTH * SHEET_SCALE
    cell_height = CANVAS_HEIGHT * SHEET_SCALE + SHEET_LABEL
    rows = math.ceil(slide_count / SHEET_COLUMNS)
    width = round(SHEET_GAP + SHEET_COLUMNS * (cell_width + SHEET_GAP))
    height = round(SHEET_GAP + rows * (cell_height + SHEET_GAP))
    arguments = [
        f"--window-size={width},{height}",
        f"--screenshot={out_path}",
        harness.as_uri() + "#sheet",
    ]
    run_chrome(browser, arguments)


def run_chrome(browser: str, arguments: list[str]) -> str:
    command = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--allow-file-access-from-files",
        f"--virtual-time-budget={VIRTUAL_TIME_MS}",
        *arguments,
    ]
    completed = subprocess.run(
        command, capture_output=True, text=True, check=False, timeout=CHROME_TIMEOUT_S
    )
    if completed.returncode != 0:
        message = f"the browser failed ({completed.returncode}): {completed.stderr.strip()[-400:]}"
        raise DeckError(message)
    return completed.stdout


# Wireframes


def wireframe(plan: SlidePlan, style: Style) -> str:
    colors = style.colors
    is_dark = plan.layout in ("title", "closing")
    background = colors["text"] if is_dark else colors["background"]
    if plan.layout == "section":
        background = colors["accent"]
    foreground = colors["background"] if is_dark or plan.layout == "section" else colors["text"]
    centered = plan.layout in ("title", "section", "statement", "closing")
    section_style = (
        f"background:{background};color:{foreground};font-family:{family(style, 'body')};"
        "padding:128px;display:flex;flex-direction:column;gap:48px;"
        + ("justify-content:center;" if centered else "")
    )
    body = wireframe_body(plan, style, foreground)
    return f'<section id="{html.escape(plan.slide_id)}" style="{section_style}">{body}</section>'


def wireframe_body(plan: SlidePlan, style: Style, foreground: str) -> str:
    big = plan.layout in ("title", "section", "statement")
    size = style.size("display") if big else style.size("title")
    tag = "h1" if plan.layout == "title" else "h2"
    heading = (
        f'<{tag} style="font-family:{family(style, "heading")};font-size:{size}px;'
        f'line-height:1.1;max-width:1500px">{html.escape(plan.title)}</{tag}>'
    )
    box = placeholder(html.escape(plan.shows or plan.layout), style, foreground)
    blank = placeholder("", style, foreground)
    accent = style.colors["accent"]
    bodies = {
        "title": f'<p style="font-size:{style.size("body")}px;opacity:.7">Presenter · date</p>',
        "section": "",
        "statement": "",
        "big-number": (
            f'<div style="display:flex;gap:48px;align-items:center;flex:1">'
            f'<p style="font-size:{style.size("number")}px;color:{accent};font-weight:700">##</p>'
            f"{box}</div>"
        ),
        "comparison": f'<div style="display:flex;gap:48px;flex:1">{box}{blank}</div>',
        "quote": (
            f'<div style="flex:1;display:flex;border-left:8px solid {accent};padding-left:48px">'
            f"{box}</div>"
        ),
        "points": (
            '<div style="display:flex;flex-direction:column;gap:24px;flex:1">'
            f"{box}{blank}{blank}</div>"
        ),
        "timeline": f'<div style="display:flex;gap:32px;flex:1">{box}{blank * 3}</div>',
    }
    return heading + bodies.get(plan.layout, box)


def placeholder(label: str, style: Style, foreground: str) -> str:
    muted = style.colors["muted"]
    return (
        f'<div style="flex:1;display:flex;align-items:center;justify-content:center;'
        f'border:3px dashed {muted};border-radius:16px;padding:32px">'
        f'<p style="font-size:{PLACEHOLDER_PX}px;color:{foreground};opacity:.6;'
        f'text-align:center">{label}</p></div>'
    )


def family(style: Style, role: str) -> str:
    face = style.fonts.get(role) or style.fonts["body"]
    return f"'{face.family}', sans-serif"


if __name__ == "__main__":
    sys.exit(main())
