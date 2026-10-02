# CHANGELOG format

## Shape

```markdown
# Harness changelog

What the harness does differently, and why. Newest first.

## 2026-09-25

- **Added** `skills/write-changelog-entry/`: harness changes get a dated what-and-why entry
  - _Why:_ <the requester's reason>
```

- **Date heading** → `## YYYY-MM-DD`, newest first, one per day; one per branch, dated the day of its latest entry
- **Entry** → `- **<Kind>** \`<path>\`: <what the agent now does>`
  - Kind is one of `Added`, `Changed`, `Removed`, `Fixed`
  - Path is relative to `.claude/`; a folder for a whole skill; comma-separate several
- **Why** → exactly one nested `  - _Why:_ <reason>`
- Nothing else: no paragraphs, tables, code blocks, or extra sub-bullets

## Limits

- Headline after the path: ≤ 15 words
- Why: ≤ 25 words
- No vague words (the lint lists them): say the specific thing instead

## Headline: behavior, not edits

- ✗ `Changed \`rules/python-errors.md\`: updated error handling rules`
- ✓ `Changed \`rules/python-errors.md\`: missing dict keys now fail loudly instead of defaulting`

## Why: the reason, not a restatement

- ✗ `_Why:_ to improve error handling`
- ✓ `_Why:_ a \`.get(..., "")\` default hid a bad config path for a week`

## What counts as a change

- **Log** → new/removed skill or rule, a rule that now says something different, a hook, a settings change, a lint limit
- **Skip** → typo, rewording that keeps the meaning, reformatting, CHANGELOG edits
