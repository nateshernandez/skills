---
paths:
  - "**/*.py"
---

# Python flow

Code reads top-down like a newspaper: the headline first, then detail in the order it's needed.

- **Arranging a module** → public entry points first, then private helpers in the order they're called
  - _Because:_ the reader meets each name before its definition and never scrolls back up
- **A function begins with special cases** → handle them as guard clauses that return or raise early
  - _Because:_ the main path stays unindented and every exit is visible at the top
- **Declaring a variable** → declare it right before its first use
  - _Because:_ distance between definition and use is distance a reader must hold in mind
- **A condition takes more than a glance to read** → assign it to a well-named variable first
  - _Because:_ the name states the intent the boolean expression only implies
  - ✗ `if user.age >= 18 and not user.banned:` ✓ `if is_eligible:`
- **A comprehension needs more than one `for` or `if`** → write a loop
  - _Because:_ nested comprehensions read inside-out; a loop reads top-down
- **Writing a chain of `isinstance` checks** → use `match`, `functools.singledispatch`, or a more precise parameter type
  - _Because:_ type ladders grow a branch per caller and hide the real contract
