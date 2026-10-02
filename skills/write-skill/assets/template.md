---
name: <kebab-case, matches folder name>
description: >
  Use when: <the task situation that should route here>.
  Not when: <the nearest task that should NOT route here>.
---

## Goal

<One line: the outcome, not the activity.>

## In

- <input>
- <input (ask if missing)>

## Out

- <artifact produced, and where>

## Flow

```mermaid
flowchart TD
  A["<step>"] --> B["<step>"]
  B --> C{"<decision?>"}
  C -- yes --> D["<step>"]
  C -- no --> B
```

## Rules

- **<situation>** → <action>
  - *Because:* <reason>

## Done When

- [ ] <checkable condition>
- [ ] <checkable condition>

## Never

- <hard no>

## More

- [references/<topic>.md](references/<topic>.md): <what it holds>
- [scripts/<name>.sh](scripts/<name>.sh): <what it does>
