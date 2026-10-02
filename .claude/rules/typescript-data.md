---
paths:
  - "**/*.ts"
---

# TypeScript data

Make illegal states unrepresentable: type the shapes once, and let the compiler hold every caller to them.

- **Input arrives from outside the code (JSON, the page, environment)** → type it `unknown` and narrow it before use
  - _Because:_ types alone don't check what arrives at runtime
- **A result or state has variants** → use a union discriminated by a literal field
  - _Because:_ the compiler then forces every caller to handle each variant
- **A value has a fixed set of options** → use a string literal union, not an `enum`
  - _Because:_ unions erase at compile time and need no import to use
- **Declaring an object shape** → use `type`, not `interface`
  - _Because:_ one way to declare shapes; `type` also covers unions and derived types
- **Reaching for `as` or `!` on data you didn't create** → narrow with a check instead
  - _Because:_ an assertion silences the checker without checking anything at runtime
