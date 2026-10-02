#!/usr/bin/env python3
"""Screenshot pages at phone and desktop widths, in light and dark, with the configured browser.

Usage: screens.py OUT_DIR TARGET [TARGET ...]
  TARGET is a route like `/settings` (joined to `app.url`), a full URL, or a local .html file.
  Writes OUT_DIR/<name>-<mobile|desktop>-<light|dark>.png and prints each path.

The `screenshots` config field is the command prefix, like `pnpm exec playwright screenshot`;
add `--load-storage=<file>` to it to capture pages behind sign-in.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from kit_config import Config, ConfigError, fill, load

COLOR_SCHEMES = ("light", "dark")
WAIT_MS = 500


class Viewport(NamedTuple):
    name: str
    size: str


VIEWPORTS = (Viewport("mobile", "390,844"), Viewport("desktop", "1280,800"))


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 1
    out_dir = Path(sys.argv[1])
    try:
        config = load()
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    if config.screenshots is None:
        print("no `screenshots` command in .claude/kit/config.json", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    any_failed = False
    for target in sys.argv[2:]:
        url = target_url(config, target)
        if url is None:
            print(f"`{target}`: a route needs `app.url` in the config", file=sys.stderr)
            any_failed = True
            continue
        any_failed |= not capture(config, url, out_dir.resolve() / page_name(target))
    return 1 if any_failed else 0


def target_url(config: Config, target: str) -> str | None:
    if re.match(r"^[a-z]+://", target):
        return target
    if target.endswith(".html"):
        return (config.root / target).resolve().as_uri()
    return config.app.url.rstrip("/") + target if config.app else None


def page_name(target: str) -> str:
    path = target.split("://", 1)[-1].split("?", 1)[0]
    if path.endswith(".html"):
        return Path(path).stem
    slug = re.sub(r"[^a-z0-9]+", "-", path.split("/", 1)[-1].lower()).strip("-")
    return slug or "home"


def capture(config: Config, url: str, name_path: Path) -> bool:
    is_ok = True
    for viewport in VIEWPORTS:
        for color_scheme in COLOR_SCHEMES:
            image_path = name_path.with_name(f"{name_path.name}-{viewport.name}-{color_scheme}.png")
            command = (
                f"{config.screenshots} --full-page --wait-for-timeout={WAIT_MS}"
                f" --viewport-size={viewport.size} --color-scheme={color_scheme}"
                f" {fill('{url} {image}', url=url, image=str(image_path))}"
            )
            completed = subprocess.run(
                command, shell=True, cwd=config.root, capture_output=True, text=True, check=False
            )
            if completed.returncode == 0:
                print(image_path)
            else:
                print(f"{image_path}: {completed.stderr.strip()[-300:]}", file=sys.stderr)
                is_ok = False
    return is_ok


if __name__ == "__main__":
    sys.exit(main())
