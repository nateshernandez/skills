---
paths:
  - "**/*.py"
---

# Python errors

Failures are loud, and they're handled only where something useful can be done about them.

- **About to write `try`** → catch only if this spot can recover or add context; otherwise let it propagate
  - _Because:_ a catch that can't act just moves the crash somewhere harder to debug
- **The function can't produce its result** → raise an exception; don't return `None` or a sentinel
  - _Because:_ every caller must remember the check, and the one that forgets fails far away
- **An edge case needs special handling** → redesign so the normal path covers it
  - _Because:_ an empty result or idempotent operation removes the error instead of handling it
  - ✗ `if not items: return None` ✓ `return [transform(item) for item in items]`
- **A required value might be missing** → index it directly and let it fail
  - _Because:_ a fallback default turns a clear `KeyError` into wrong output downstream
  - ✗ `config.get("path", "")` ✓ `config["path"]`
- **Checking something the types already rule out** → delete the check
  - _Because:_ an impossible branch is dead code that suggests the types lie
- **Guarding an internal invariant vs rejecting caller input** → `assert` the invariant; `raise` for bad input
  - _Because:_ assert documents "can't happen"; raise tells the caller what they did wrong
