#!/usr/bin/env python3
"""Show which rule files load together and flag similar rules across them.

Usage: check_rules.py [RULES_DIR ...]   (default: .claude/rules)
Exit 1 if two rules that load together look like duplicates or conflicts.
"""

import re
import sys
from itertools import combinations, product
from pathlib import Path
from typing import NamedTuple

from lint_rule import RULE_RE, is_always_on, parse_paths, split_frontmatter

MIN_RULE_SIMILARITY = 0.4
STOPWORDS = frozenset(
    [
        *("a", "an", "the", "and", "or", "of", "to", "for", "in", "on", "at", "by"),
        *("with", "from", "into", "it", "its", "is", "are", "be", "this", "that"),
        *("you", "your", "about", "when", "not", "no", "any", "some", "one", "only"),
    ]
)
GLOB_TOKEN_REGEX = {"**/": "(?:.*/)?", "**": ".*", "*": "[^/]*", "?": "[^/]"}


class Rule(NamedTuple):
    file_name: str
    situation: str
    keywords: frozenset[str]


class RuleFile(NamedTuple):
    name: str
    globs: list[str]
    always_on: bool
    rules: list[Rule]


class SimilarPair(NamedTuple):
    similarity: float
    first: Rule
    second: Rule


def main() -> int:
    rules_dirs = [Path(arg) for arg in sys.argv[1:]] or [Path(".claude/rules")]
    rule_files = [
        load_rule_file(rule_path)
        for rules_dir in rules_dirs
        for rule_path in sorted(rules_dir.glob("*.md"))
    ]
    if not rule_files:
        print("no rule files found")
        return 0
    print_scopes(rule_files)
    print_load_together(rule_files)

    similar_pairs = find_similar_rules(rule_files)
    if not similar_pairs:
        print("\nno similar rules")
        return 0
    print("\nSimilar rules that load together (merge or sharpen):")
    for pair in similar_pairs:
        print(
            f"  {pair.similarity:.0%}  {pair.first.file_name}: {pair.first.situation}"
            f"  <>  {pair.second.file_name}: {pair.second.situation}"
        )
    return 1


def load_rule_file(rule_path: Path) -> RuleFile:
    frontmatter, body = split_frontmatter(rule_path.read_text())
    body_lines = [line for line in body.splitlines() if line.strip()]
    rule_matches = [match for line in body_lines if (match := RULE_RE.match(line))]
    rules = [
        Rule(
            rule_path.name,
            match.group("situation"),
            rule_keywords(f"{match.group('situation')} {match.group('action')}"),
        )
        for match in rule_matches
    ]
    globs = parse_paths(frontmatter or "")
    return RuleFile(rule_path.name, globs, is_always_on(body_lines), rules)


def rule_keywords(text: str) -> frozenset[str]:
    words = re.findall(r"[a-z][a-z0-9-]+", text.lower())
    return frozenset(word.rstrip("s") for word in words if word not in STOPWORDS)


def print_scopes(rule_files: list[RuleFile]) -> None:
    name_width = max(len(rule_file.name) for rule_file in rule_files)
    for rule_file in rule_files:
        scope = "always on" if rule_file.always_on else ", ".join(rule_file.globs) or "(no paths)"
        print(f"{rule_file.name:<{name_width}}  {len(rule_file.rules)} rules  {scope}")


def print_load_together(rule_files: list[RuleFile]) -> None:
    print("\nLoad together:")
    for first, second in combinations(rule_files, 2):
        if load_together(first, second):
            print(f"  {first.name} + {second.name}")


def load_together(first: RuleFile, second: RuleFile) -> bool:
    if first.always_on or second.always_on:
        return True
    all_globs = first.globs + second.globs
    extensions = {ext for glob in all_globs for ext in re.findall(r"\*(\.[\w.]+)$", glob)}
    leaf_names = ["x", *(f"x{extension}" for extension in sorted(extensions))]
    return any(
        glob_covers(first_glob, second_glob, leaf_names)
        or glob_covers(second_glob, first_glob, leaf_names)
        for first_glob, second_glob in product(first.globs, second.globs)
    )


def glob_covers(glob: str, other_glob: str, leaf_names: list[str]) -> bool:
    pattern = glob_to_regex(glob)
    return any(pattern.fullmatch(path) for path in sample_paths(other_glob, leaf_names))


def glob_to_regex(glob: str) -> re.Pattern[str]:
    tokens = re.split(r"(\*\*/|\*\*|\*|\?)", glob)
    return re.compile("".join(GLOB_TOKEN_REGEX.get(token, re.escape(token)) for token in tokens))


def sample_paths(glob: str, leaf_names: list[str]) -> list[str]:
    samples = []
    for directories in ("", "a/"):
        for leaf_name in leaf_names:
            sample = glob[:-2] + directories + leaf_name if glob.endswith("**") else glob
            samples.append(sample.replace("**/", directories).replace("*", "x").replace("?", "x"))
    return samples


def find_similar_rules(rule_files: list[RuleFile]) -> list[SimilarPair]:
    comparable_rules = [rule for rule_file in rule_files for rule in rule_file.rules]
    by_name = {rule_file.name: rule_file for rule_file in rule_files}
    similar_pairs = []
    for first, second in combinations(comparable_rules, 2):
        first_file, second_file = by_name[first.file_name], by_name[second.file_name]
        if first_file is not second_file and not load_together(first_file, second_file):
            continue
        if not first.keywords or not second.keywords:
            continue
        similarity = len(first.keywords & second.keywords) / len(first.keywords | second.keywords)
        if similarity >= MIN_RULE_SIMILARITY:
            similar_pairs.append(SimilarPair(similarity, first, second))
    return sorted(similar_pairs, reverse=True)


if __name__ == "__main__":
    sys.exit(main())
