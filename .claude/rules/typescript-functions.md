---
paths:
  - "**/*.ts"
---

# TypeScript functions

A function does one thing at one level of abstraction; a file exports few, deep functions and hides the rest.

- **The function's honest name needs "and"** → split it into one function per job
  - _Because:_ two jobs in one body can't be tested, reused, or named separately
- **Decisions are tangled with the page, network, or file system** → decide in pure functions; do the I/O in a thin caller
  - _Because:_ pure code tests without a browser and reads without tracking state
- **About to export something** → export only what another file calls today
  - _Because:_ every export is an interface to keep stable; unexported code changes freely
- **Adding a parameter, option, or overload no caller uses yet** → leave it out
  - _Because:_ speculative flexibility is guessed wrong more often than right, and still costs reading
- **A function takes more than two arguments, or two of one type** → take one object
  - _Because:_ named fields can't be swapped by accident and read clearly at the call site
  - ✗ `checkTargets(page, 44, true)` ✓ `checkTargets(page, { minPx: 44, isTouch: true })`
- **Writing a named function** → use a `function` declaration; arrows for callbacks only
  - _Because:_ one shape reads consistently and names itself in stack traces
- **Exporting a function** → annotate its return type
  - _Because:_ the return type is the contract callers rely on; inference lets an edit widen it silently
