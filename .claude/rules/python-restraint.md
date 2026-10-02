---
paths:
  - "**/*.py"
---

# Python restraint

Write the least code that solves today's problem; every extra part must be read and kept in sync.

- **Adding a parameter, option, or hook no caller uses yet** → leave it out
  - _Because:_ speculative flexibility is guessed wrong more often than right, and still costs reading
- **An abstraction has one implementation** → inline it
  - _Because:_ indirection earns its cost only when there is something to choose between
- **A function or class only forwards to another** → delete it and call the target
  - _Because:_ a pass-through adds a name to learn and a hop to follow for nothing
- **Changing a signature only this repo calls** → update every caller; add no compatibility shim
  - _Because:_ shims for callers you control are dead weight from day one
- **Debug prints, temporary logging, or scaffolding remain** → remove them before finishing
  - _Because:_ leftover scaffolding reads as intended behavior to the next reader
