---
id: <spec id>
status: <done | blocked>
rounds: <review rounds run>
---

# <Feature name>: report

<One line: what shipped, or what blocks it.>

## Behaviors

- ✓ **<n>.B1 <situation>** → `<acceptance test file>`
- ✗ **<n>.B2 <situation>** → <why it doesn't hold yet>

## Blocked on

- **<blocker finding still open>** → <the one question for the requester>

## Decided without you

- **<situation>** → <what was chosen>
  - _Because:_ <reason>

## Codified

- **`docs/decisions/<NNNN>-<slug>.md`** → <the decision in one line>
- **`.claude/rules/<scope>-<concern>.md`** → <what the rule makes future code do>

## Open notes

- **[note] <lens> · <n.Bk or file:line>** → <finding>

## Skipped

- **<step a turbo build cut>** → <what it would have checked>

## Try it

- `<command that runs the app>` → <where to go and what to do there>

## Screens

![<caption>](screens/<file>.png)
