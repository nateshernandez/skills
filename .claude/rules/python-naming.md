---
paths:
  - "**/*.py"
---

# Python naming

Names are for a reader who sees only the signature: they should know what to pass and what comes back.

- **Naming anything** → use the word the domain, columns, and tests already use, spelled out
  - _Because:_ generic names describe nothing; abbreviations and second vocabularies cost every reader a lookup
  - ✗ `data`, `tmp`, `disc_val` ✓ `line_items`, `discount_value`
- **Arguments travel together** → spell them as a set
  - _Because:_ asymmetry makes a reader hunt for a distinction that isn't there
  - ✗ `value`, `discount_type` ✓ `discount_value`, `discount_type`
- **A name carries units or scale** → make the name match the value
  - _Because:_ a name that lies about magnitude survives review and becomes a real bug
  - ✗ `timeout_seconds = 500` (ms) ✓ `timeout_ms = 500`
- **A function shares a name with a field, key, column, or attribute nearby** → name the operation
  - _Because:_ every call site becomes ambiguous even when Python resolves it fine
  - ✗ `def discount()` beside `order.discount` ✓ `def resolve_discount()`
- **You reached for a synonym because the obvious name was taken** → rename the thing that took it
  - _Because:_ the taker is the misnamed one; working around it spreads the confusion
- **Naming a bool or a function returning one** → phrase it as a yes/no question
  - _Because:_ `if valid:` hides whether it's a flag, a validator, or a result
  - ✗ `valid`, `check_discount()` ✓ `is_valid`, `has_discount()`
- **A docstring's first sentence explains the arguments** → rename the arguments instead
  - _Because:_ the docstring's job is the non-obvious why, not what the parameters are
- **A name is wrong and call sites are few** → rename it now
  - _Because:_ renaming gets expensive once the name spreads
