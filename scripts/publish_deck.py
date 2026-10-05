#!/usr/bin/env python3
"""Move a deck between decks/<id>/ and the files of a Claude Slides artifact.

Usage:
  publish_deck.py stage DECK_DIR OUT_DIR
      write OUT_DIR/project/deck.json and every changed project/slides/<id>.html, with each
      assets/ image swapped for its uploaded /_blob/ URL; print the Artifact publish call's
      root, file_path, and files as JSON. Exit 1, naming each file, if an image isn't uploaded.
  publish_deck.py record DECK_DIR [--url URL] [--asset PATH=BLOB_URL ...]
      save the artifact's URL, or an uploaded image's /_blob/ URL, in published.json
  publish_deck.py pull DECK_DIR SAVED_DIR
      copy slides an Artifact read saved under SAVED_DIR/project/slides/ back into slides/,
      swapping /_blob/ URLs back to assets/ paths; print each slide that changed

published.json remembers what was last staged, so stage sends only slides that changed and
removes slides the storyline dropped.
"""

import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from kit_config import project_root
from kit_deck import (
    PUBLISHED_NAME,
    SLIDES_NAME,
    DeckError,
    Storyline,
    Style,
    face_key,
    load_storyline,
    load_style,
    read_json,
    slide_paths,
    style_path,
)

SRC_RE = re.compile(r'(?P<attribute>src=")(?P<src>[^"]+)(?P<end>")')
DECK_JSON_VERSION = 4


def main() -> int:
    arguments = sys.argv[1:]
    commands = {"stage": stage_command, "record": record_command, "pull": pull_command}
    if not arguments or arguments[0] not in commands:
        print(__doc__, file=sys.stderr)
        return 1
    try:
        return commands[arguments[0]](arguments[1:])
    except DeckError as error:
        print(error, file=sys.stderr)
        return 1


def stage_command(arguments: list[str]) -> int:
    if len(arguments) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    deck_dir, out_dir = Path(arguments[0]).resolve(), Path(arguments[1]).resolve()
    storyline = load_storyline(deck_dir)
    style = load_style(style_path(deck_dir, project_root()))
    published = load_published(deck_dir)
    sources = {path.stem: path.read_text() for path in slide_paths(deck_dir)}
    missing = sorted(
        {src for text in sources.values() for src in local_sources(text)} - set(published["assets"])
    )
    if missing:
        print("Upload these first, then `record --asset PATH=BLOB_URL` each:", file=sys.stderr)
        print("\n".join(f"  {deck_dir / path}" for path in missing), file=sys.stderr)
        return 1
    published.setdefault("created_at", datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    call = stage(storyline, style, sources, published, out_dir)
    save_published(deck_dir, published)
    print(json.dumps(call, indent=2))
    return 0


def stage(
    storyline: Storyline, style: Style, sources: dict[str, str], published: dict, out_dir: Path
) -> dict:
    slides_dir = out_dir / "project" / SLIDES_NAME
    slides_dir.mkdir(parents=True, exist_ok=True)
    deck_json_path = out_dir / "project" / "deck.json"
    deck_json_path.write_text(json.dumps(deck_json(storyline, style, published), indent=2))
    hashes: dict[str, str] = published.setdefault("hashes", {})
    files: dict[str, str | None] = {}
    for slide_id, text in sources.items():
        staged = to_blobs(text, published["assets"])
        digest = hashlib.sha256(staged.encode()).hexdigest()
        if hashes.get(slide_id) == digest:
            continue
        (slides_dir / f"{slide_id}.html").write_text(staged)
        files[f"project/{SLIDES_NAME}/{slide_id}.html"] = f"project/{SLIDES_NAME}/{slide_id}.html"
        hashes[slide_id] = digest
    for dropped in sorted(set(hashes) - set(sources)):
        files[f"project/{SLIDES_NAME}/{dropped}.html"] = None
        del hashes[dropped]
    return {
        "url": published.get("url"),
        "root": str(out_dir),
        "file_path": str(deck_json_path),
        "files": files,
    }


def deck_json(storyline: Storyline, style: Style, published: dict) -> dict:
    order = [plan.slide_id for plan in storyline.slides]
    sections = {
        "s1": {"description": storyline.labels.get("Ask", storyline.title), "start": order[0]}
    }
    for plan in storyline.slides[1:]:
        if plan.layout == "section":
            sections[f"s{len(sections) + 1}"] = {"description": plan.title, "start": plan.slide_id}
    faces = {
        face_key(face.family): {"family": face.family, "href": face.href}
        for face in style.fonts.values()
        if face.href
    }
    return {
        "v": DECK_JSON_VERSION,
        "createdOnFiles": {"v": 1, "at": published["created_at"]},
        "lists": "css",
        "title": storyline.title,
        "order": order,
        "cover": order[0],
        "sections": sections,
        "faces": faces,
        "designSystems": [],
    }


def local_sources(text: str) -> list[str]:
    return [
        m.group("src") for m in SRC_RE.finditer(text) if not m.group("src").startswith("/_blob/")
    ]


def to_blobs(text: str, assets: dict[str, str]) -> str:
    return SRC_RE.sub(
        lambda m: (
            f"{m.group('attribute')}{assets.get(m.group('src'), m.group('src'))}{m.group('end')}"
        ),
        text,
    )


def record_command(arguments: list[str]) -> int:
    if not arguments:
        print(__doc__, file=sys.stderr)
        return 1
    deck_dir = Path(arguments[0]).resolve()
    published = load_published(deck_dir)
    flags = arguments[1:]
    for flag, value in zip(flags[::2], flags[1::2], strict=True):
        if flag == "--url":
            published["url"] = value
        elif flag == "--asset" and "=" in value:
            path, blob_url = value.split("=", 1)
            published["assets"][path] = blob_url
        else:
            message = f"unknown flag `{flag} {value}`; see --url and --asset PATH=BLOB_URL"
            raise DeckError(message)
    save_published(deck_dir, published)
    print(deck_dir / PUBLISHED_NAME)
    return 0


def pull_command(arguments: list[str]) -> int:
    if len(arguments) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    deck_dir, saved_dir = Path(arguments[0]).resolve(), Path(arguments[1]).resolve()
    published = load_published(deck_dir)
    blobs = {blob_url: path for path, blob_url in published["assets"].items()}
    hashes: dict[str, str] = published.setdefault("hashes", {})
    for saved_path in sorted((saved_dir / "project" / SLIDES_NAME).glob("*.html")):
        remote = saved_path.read_text()
        hashes[saved_path.stem] = hashlib.sha256(remote.encode()).hexdigest()
        local_path = deck_dir / SLIDES_NAME / saved_path.name
        local = SRC_RE.sub(
            lambda m: (
                f"{m.group('attribute')}{blobs.get(m.group('src'), m.group('src'))}{m.group('end')}"
            ),
            remote,
        )
        if not local_path.exists() or local_path.read_text() != local:
            local_path.write_text(local)
            print(f"changed: {local_path}")
    save_published(deck_dir, published)
    return 0


def load_published(deck_dir: Path) -> dict:
    path = deck_dir / PUBLISHED_NAME
    published = read_json(path) if path.exists() else {}
    if not isinstance(published, dict):
        message = f"{path}: must be a JSON object"
        raise DeckError(message)
    published.setdefault("assets", {})
    return published


def save_published(deck_dir: Path, published: dict) -> None:
    (deck_dir / PUBLISHED_NAME).write_text(json.dumps(published, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    sys.exit(main())
