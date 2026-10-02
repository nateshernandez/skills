---
paths:
  - "**/*.ts"
---

# TypeScript naming

Names are for a reader who sees only the call site; they use the domain's words and say what kind of thing they are.

- **Naming anything** → use the word the domain and tests already use, spelled out
  - _Because:_ generic names describe nothing; abbreviations and synonyms cost every reader a lookup
  - ✗ `data`, `res`, `el` ✓ `problems`, `result`, `element`
- **Choosing the case** → `UpperCamelCase` types, `lowerCamelCase` values and functions, `UPPER_SNAKE_CASE` module constants
  - _Because:_ the case tells a reader what kind of thing a name is before they look it up
  - ✓ `UxProblem`, `smallTapTargets`, `MIN_TAP_PX`
- **Naming a file** → kebab-case, named after its main export or its job
  - _Because:_ searching for the export finds the file, and case-insensitive file systems never collide
- **Naming a function** → verb plus the domain noun, or the noun it returns
  - _Because:_ callers read what happens without opening it
- **Naming a boolean** → phrase it as a yes/no question
  - _Because:_ `if (hidden)` hides whether it's a flag, a check, or a result
  - ✗ `hidden`, `clamped` ✓ `isHidden`, `isClamped`
- **A name carries units or scale** → put the unit in the name
  - _Because:_ a name that lies about magnitude survives review and becomes a real bug
  - ✗ `minSize = 44` ✓ `minPx = 44`
- **Exporting** → use named exports
  - _Because:_ named exports keep one name everywhere, so renames and searches find every use
