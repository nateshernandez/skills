---
paths:
  - "**/*.py"
---

# Python functions

A function does one thing at one level of abstraction, and its name says what that thing is.

- **The function's honest name needs "and"** → split it into one function per job
  - _Because:_ two jobs in one body can't be tested, reused, or named separately
  - ✗ `def load_and_validate()` ✓ `config = validate(load(path))`
- **Decisions are tangled with reading or writing files, network, or output** → compute in pure functions; do I/O in a thin caller
  - _Because:_ pure code tests without fixtures and reads without tracking state
- **One body mixes high-level steps with low-level detail** → extract the detail into named helpers
  - _Because:_ a reader should skim the steps and dive into a helper only when needed
- **Callers must call things in a set order or pass mode flags** → hide the sequence inside one deeper function
  - _Because:_ a small interface over real work beats many shallow calls every caller must orchestrate
- **A class has `__init__` plus one method** → make it a function
  - _Because:_ the class is ceremony around a call; its state lives for one invocation
  - ✗ `Parser(text).parse()` ✓ `parse(text)`
- **A nested `def` captures nothing from the enclosing function** → move it to a module-level `_helper`
  - _Because:_ nesting hides it from tests and suggests a closure that isn't there
- **Returning more than two values** → return a `NamedTuple` or frozen dataclass
  - _Because:_ positional unpacking breaks silently when the order changes
