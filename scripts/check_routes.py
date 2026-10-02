#!/usr/bin/env python3
"""Show every skill's routing clauses side by side and flag likely collisions.

Usage: check_routes.py [SKILLS_DIR ...]   (default: .claude/skills)
Exit 1 if any pair of `Use when:` clauses overlaps past the threshold.
"""

import re
import sys
from itertools import combinations
from pathlib import Path
from typing import NamedTuple

from lint_skill import parse_frontmatter, split_frontmatter

MIN_COLLISION_OVERLAP = 0.3
STOPWORDS = frozenset(
    [
        *("a", "an", "the", "and", "or", "of", "to", "for", "in", "on", "at", "by"),
        *("with", "from", "into", "user", "asks", "asking", "wants", "want", "when"),
        *("use", "not", "is", "are", "be", "it", "its", "this", "that", "these"),
        *("those", "some", "any", "needed", "need"),
    ]
)


class Route(NamedTuple):
    name: str
    use_when: str
    not_when: str


class Collision(NamedTuple):
    overlap: float
    first_name: str
    second_name: str
    shared_keywords: list[str]
    is_resolved: bool


def main() -> int:
    skills_dirs = [Path(arg) for arg in sys.argv[1:]] or [Path(".claude/skills")]
    routes = load_routes(skills_dirs)
    if not routes:
        print("no skills found")
        return 0
    print_routes(routes)

    collisions = find_collisions(routes)
    for collision in collisions:
        status = "resolved by Not when" if collision.is_resolved else "COLLISION"
        print(
            f"\n{status}: {collision.first_name} <> {collision.second_name}  "
            f"overlap {collision.overlap:.0%}  shared: {', '.join(collision.shared_keywords)}"
        )
    if any(not collision.is_resolved for collision in collisions):
        print("\nSharpen `Not when:` on both so each names what makes the other distinct.")
        return 1
    print("\nno unresolved collisions")
    return 0


def load_routes(skills_dirs: list[Path]) -> list[Route]:
    routes = []
    for skills_dir in skills_dirs:
        for skill_path in sorted(skills_dir.glob("*/SKILL.md")):
            frontmatter, _ = split_frontmatter(skill_path.read_text())
            fields = parse_frontmatter(frontmatter or "")
            use_when, not_when = routing_clauses(fields.get("description", ""))
            routes.append(Route(fields.get("name", skill_path.parent.name), use_when, not_when))
    return routes


def routing_clauses(description: str) -> tuple[str, str]:
    use_when_match = re.search(r"Use when:(.*?)(?:Not when:|$)", description, re.DOTALL)
    not_when_match = re.search(r"Not when:(.*)$", description, re.DOTALL)
    use_when = use_when_match.group(1).strip() if use_when_match else ""
    not_when = not_when_match.group(1).strip() if not_when_match else ""
    return use_when, not_when


def print_routes(routes: list[Route]) -> None:
    name_width = max(len(route.name) for route in routes)
    for route in routes:
        print(f"{route.name:<{name_width}}  USE  {route.use_when or '(missing)'}")
        print(f"{'':<{name_width}}  NOT  {route.not_when or '(missing)'}")


def find_collisions(routes: list[Route]) -> list[Collision]:
    collisions = []
    for first, second in combinations(routes, 2):
        first_keywords = routing_keywords(first.use_when)
        second_keywords = routing_keywords(second.use_when)
        if not first_keywords or not second_keywords:
            continue
        shared_keywords = first_keywords & second_keywords
        overlap = len(shared_keywords) / len(first_keywords | second_keywords)
        if overlap >= MIN_COLLISION_OVERLAP:
            is_resolved = excludes(first, second) and excludes(second, first)
            collisions.append(
                Collision(overlap, first.name, second.name, sorted(shared_keywords), is_resolved)
            )
    return sorted(collisions, reverse=True)


def routing_keywords(clause: str) -> set[str]:
    words = re.findall(r"[a-z][a-z0-9-]+", clause.lower())
    return {word.rstrip("s") for word in words if word not in STOPWORDS}


def excludes(route: Route, other: Route) -> bool:
    distinctive_keywords = routing_keywords(other.use_when) - routing_keywords(route.use_when)
    return bool(distinctive_keywords & routing_keywords(route.not_when))


if __name__ == "__main__":
    sys.exit(main())
