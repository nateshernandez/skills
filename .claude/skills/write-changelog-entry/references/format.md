# CHANGELOG.md format

## Shape

```markdown
# Changelog

What each release of kit changes for the people using it. Newest first.

## 0.3.0 (2026-10-09)

- **Added** `/kit:<skill>`: <what a user can now do>
- **Changed** <the thing users touch>: <how it behaves now>
```

- **Version heading** → `## X.Y.Z (YYYY-MM-DD)`, newest first, dated the release day
  - X.Y.Z is the new `version` in `.claude-plugin/plugin.json`
- **Entry** → `- **<Kind>** <subject>: <what the user now gets>`
  - Kind is `Added`, `Changed`, `Removed`, or `Fixed`; group entries in that order
  - Subject is what the user touches: a `/kit:` command, a script in the gate, a config field, a file setup copies, or a role such as "the UX review"
- Nothing else: no Why line, sub-bullets, paragraphs, or tables

## Finding the commits

```bash
git log --oneline "$(git log --grep='^Release ' -1 --format=%H)"..HEAD
```

## Headline: effect, not edit

- ✗ `**Changed** \`skills/review-ux/\`: updated the blocker list`
- ✓ `**Changed** the UX review's blocker bar: tap targets under 44px and failed contrast now block`

## Breaking changes: say what to do

- ✗ `**Changed** the gate config: renamed a field`
- ✓ `**Changed** \`.claude/kit/config.json\`: \`gate\` is now \`check\`; rename it or rerun \`/kit:setup\``

## What counts

- **Log** → a new, changed, or removed skill, agent, hook, gate script, config field, or file setup copies into projects
- **Skip** → CI, this repo's `.claude/` rules and skills, README or `docs/` wording, refactors with no behavior change
