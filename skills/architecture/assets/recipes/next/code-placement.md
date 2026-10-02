---
paths:
  - "src/**/*.ts"
  - "src/**/*.tsx"
---

# Code placement

Every file has one home, found by the question tree in docs/architecture.md; folder names say what's inside.

- **Creating a file** → place it with "Where code goes" in docs/architecture.md before writing it
  - _Because:_ the home is a few questions away; a wrong one costs a move later
- **Writing a page, layout, or route handler** → build who's asking, call use cases, then render or respond; nothing more
  - _Because:_ logic in a route can't be reused by forms, endpoints, or other modules
- **Adding something a person or module can do** → a new verb-noun file in the module's `use-cases/`, exported from `server.ts`
  - _Because:_ the folder then reads as the module's list of actions
  - ✗ another function in a 900-line `server.ts` ✓ `use-cases/close-invoice.ts`
- **A use case needs a decision (status, limit, price, permission, prompt)** → a pure function in `domain/`, tested there
  - _Because:_ rules tested without a database stay fast, and readable without the framework
- **Writing a query or calling an outside service** → put it in `infra/`; keep the decisions in `domain/`
  - _Because:_ storage code stays swappable, and rules stay testable without mocks
- **Another module needs something** → export it from the owner's `index.ts` or `server.ts`; the dependent calls the owner
  - _Because:_ an entry is a promise; everything behind it can change freely
- **A file nears 250 lines** → split it by job: one use case, component, or set of rules per file
  - _Because:_ a reader holds a short file whole; `check_shape.py` fails past the cap
- **A lint or shape error fires** → move the code to the home it names; ask before loosening the lint or the baseline
  - _Because:_ the checks are the architecture; a loosened one lets it decay silently
