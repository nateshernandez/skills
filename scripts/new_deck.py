#!/usr/bin/env python3
"""Create decks/<NNN>-<slug>/storyline.md from the template, numbered after the newest deck.

Usage: new_deck.py SLUG   (kebab-case, e.g. q3-board-update)
Prints the new storyline's path. Numbers only count up, so a deck's number is its creation order.
"""

import sys
from pathlib import Path

from kit_config import project_root
from kit_deck import DECKS_PATH, STORYLINE_NAME
from new_spec import SLUG_RE, next_spec_number

TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "write-deck"
    / "assets"
    / "storyline-template.md"
)


def main() -> int:
    if len(sys.argv) != 2 or not SLUG_RE.fullmatch(sys.argv[1]):
        print(__doc__, file=sys.stderr)
        return 1
    decks_dir = project_root() / DECKS_PATH
    deck_id = f"{next_spec_number(decks_dir):03d}-{sys.argv[1]}"
    storyline_path = decks_dir / deck_id / STORYLINE_NAME
    storyline_path.parent.mkdir(parents=True)
    storyline_path.write_text(TEMPLATE_PATH.read_text().replace("<id>", deck_id))
    print(storyline_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
