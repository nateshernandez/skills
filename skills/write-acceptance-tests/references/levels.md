# Test levels

Every gate runs the tests, so every end-to-end test is paid for again on each later build. A behavior gets the cheapest test that can fail when the behavior breaks.

## Levels

- **Unit** → a function, reducer, validator, or use case called directly; milliseconds
  - Vitest or Jest, in `tests.unit.acceptance`
- **Component** → a component rendered with props and driven like a person; tens of milliseconds
  - Vitest with jsdom or happy-dom, in `tests.unit.acceptance`, when the project has it installed
- **End to end** → the built app in a real browser; seconds each, plus a server
  - Playwright, in `tests.acceptance`, each with a `// e2e:` reason

## Choosing

- **Rules** → what is allowed, how much, in what order, what text results: unit
  - Validation, status moves, permissions, pricing, formatting, error messages
- **One piece of UI** → what it shows for given props, and what it calls: component
  - Empty, loading, and error states; a form's field errors; a confirm dialog's labels
- **Needs a real browser** → focus order, keyboard use, layout at a width, navigation, scrolling: end to end
  - Only the one behavior that needs it; its rules are still unit tests
- **A journey where a miss costs the most** → money, sign-in, data loss, permissions across pages: end to end
  - One test per journey, not one per step
- **The layers must be wired together** → a server action reaches the database and the page: end to end
  - One happy path per feature proves the wiring; edge cases stay unit
- **An invariant from design.md** → unit, always
  - It names a rule of the data or protocol, so no browser is needed

## Budget

- `tests.e2e_per_spec` (4 when unset) caps a spec's end-to-end tests; `check_coverage.py` fails past it
- A spec that is mostly screens may need more; the orchestrator raises the config value for it, never the author
- The plan's Tests section may split one behavior's proof: its rules at unit level, one end-to-end test for the wiring. Give the end-to-end test the behavior's ID and the unit tests none, or a title with no ID, since the ID is used once.

## Smells

- An end-to-end test that fills three forms to reach one assertion: move the assertion to unit level and reach it directly
- An end-to-end test with no `// e2e:` reason you can say aloud: it is a unit test
- Two end-to-end tests that differ only by input: one test, or a unit test with a table of inputs
