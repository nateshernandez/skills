# Probe ideas

Acceptance tests prove the path the spec names. Probes try the paths next to it.

- **Inputs** → empty, whitespace, very long, unicode, leading/trailing spaces, pasted with a newline
- **Repeats** → double-click submit, submit twice, the same data again, the same request in parallel
- **Navigation** → refresh after success, back button, deep link straight to the page
- **States** → what shows while waiting, after an error, with nothing to show yet
- **Keyboard** → Enter submits, Tab reaches every control
- **Persistence** → restart or reload: is the result still true where the spec says it should be?
- **Viewport** → 390px and 1280px both complete the main task
- **Interfaces without a screen** → wrong types, missing fields, out-of-order calls, concurrent callers

Title each probe `<n>.B<k> probe: <what it tries>` with the full ID, so findings and the report can point at it.
