---
paths:
  - "**/*.py"
---

# Python data

Make illegal states unrepresentable: parse input once at the edge, then trust the types everywhere inside.

- **Raw input arrives (CLI args, JSON, file text)** → parse it into a typed object at the boundary, once
  - _Because:_ validation scattered inward repeats itself and still misses cases
- **Structured data crosses a function boundary** → define a `NamedTuple` or frozen dataclass, not a `dict` or bare tuple
  - _Because:_ fields get names, types, and editor completion; key typos become type errors
  - ✗ `{"name": n, "lines": k}` ✓ `Section(name=n, lines=k)`
- **A string or int has a fixed set of valid values** → use an `Enum` or `Literal`
  - _Because:_ the type checker then rejects the typo a bare string lets through
- **Reaching for `typing.cast`** → narrow with `isinstance` or `assert` instead
  - _Because:_ `cast` silences the checker without checking anything at runtime
- **About to write a base class or ABC** → use a `Protocol` or plain function; subclass only for true is-a
  - _Because:_ inheritance couples both sides to every future change in the parent
