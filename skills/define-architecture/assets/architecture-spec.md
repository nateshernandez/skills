---
id: <id>
status: draft
size: L
---

# App architecture

Anyone finds where code goes from one page, and code in the wrong place fails a check seconds after it's written.

## Decide

- **<n>.D1 Homes for code** → routes, business modules, shared UI, platform, and pure helpers; imports flow one way
  - _Alt:_ one shared folder for everything reused; fewer homes, but it becomes the junk drawer (tech lens)
- **<n>.D2 Inside a module** → use cases, domain rules, infrastructure, and components, each a flat folder; imports point inward
  - _Alt:_ an entry file plus a data folder; fewer folders, but entry files grow past 2,000 lines (tech lens)
- **<n>.D3 A use case's shape** → one per file, taking who's asking and raw input; edges build who's asking
  - _Alt:_ each use case opens its own session; callers can't share a transaction, so copies appear (tech lens)
- **<n>.D4 Testing logic** → domain rules tested without mocks; use cases against a real test database
  - _Alt:_ mock storage in every use case test; faster, but tests mirror query order (quality lens)
- **<n>.D5 Size and shape** → source files stay under <max lines> lines; module files match their folder's kinds
  - _Alt:_ guidance only; no check, but files grow until nobody reads them whole (product lens)

## Behaviors

- **<n>.B1 Reader opens the architecture guide** → one question tree places any code; a diagram shows homes and import directions
- **<n>.B2 Shared code imports a module or a route** → lint fails, naming the boundary and the guide
- **<n>.B3 Code outside a module imports a file inside it** → lint fails, naming the public entry to use instead
- **<n>.B4 Domain code imports storage, UI, a framework, or a use case** → lint fails, naming where that code goes
- **<n>.B5 A module's components import a use case, storage, or another module** → lint fails, naming the fix
- **<n>.B6 Browser code imports server-only code** → lint fails before the build does
  - _Because:_ security lens; secrets and data access must never reach the browser bundle
- **<n>.B7 Code outside platform or a module's infrastructure reads secrets from the environment** → lint fails
  - _Because:_ security lens; one short list of folders to audit for secrets
- **<n>.B8 Two modules import each other, directly or through a third** → lint fails, naming the cycle
- **<n>.B9 A file lands where a module has no place for it, or passes <max lines> lines** → `check_shape.py` fails, naming where it goes
- **<n>.B10 Claude writes a file breaking any of these** → the problem comes back in that same turn
- **<n>.B11 Claude opens a source or React file** → the code placement and React rules load with it
- **<n>.B12 Check runs on the existing tree** → baselined files pass while they don't grow; new violations fail

## Not doing

- Moving existing code; each move in moves.md is its own spec
- Platform pieces no feature uses yet, like a database client or session, until a feature needs one
- An example module; the guide's examples are the reference
- Monorepo packages or a module generator
