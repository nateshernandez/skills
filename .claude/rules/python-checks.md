---
paths:
  - "**/*.py"
---

# Python checks

`ruff.toml` and `pyrightconfig.json` at the workspace root define what counts as a problem; the editor reads the same files.

- **Finished editing a Python file** → run `ruff check --fix`, `ruff format`, and `uv tool run pyright` on it until clean
  - _Because:_ these are the squiggles the user sees in the editor; clean here means clean there
- **A check fires and the code is right** → suppress that one code and write the reason on the same line
  - _Because:_ the reason turns a suppression into a documented decision
  - ✗ `# noqa: E501` ✓ `# noqa: E501 -- URL can't be wrapped`
- **Tempted to loosen `ruff.toml` or `pyrightconfig.json`** → ask the user first
  - _Because:_ the config is shared with the editor and every other file
- **A complexity, size, or argument-count check fires** → restructure the code; never suppress it
  - _Because:_ these checks measure design; a suppression hides the smell instead of fixing it
