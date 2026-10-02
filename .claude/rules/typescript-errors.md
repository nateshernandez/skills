---
paths:
  - "**/*.ts"
---

# TypeScript errors

Failures are loud, and they're handled only where something useful can be done about them.

- **About to write `try` or `.catch`** → catch only where this spot can recover or add context
  - _Because:_ a catch that can't act just moves the crash somewhere harder to debug
- **A dependency or setup step is missing** → throw an error that names what to install or run
  - _Because:_ the person reading it is in another project and can't see this file's intent
  - ✗ `throw new Error('import failed')` ✓ `throw new Error('UX checks need @axe-core/playwright: add it to devDependencies')`
- **Something fails that should never happen** → throw; don't return an empty result
  - _Because:_ an empty list reads as "no problems found" and hides the bug
- **Checking a case the types already rule out** → delete the check
  - _Because:_ an impossible branch is dead code that suggests the types lie
