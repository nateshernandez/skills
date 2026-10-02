---
paths:
  - "**/*.py"
---

# Python comments

Comments are a cost, not a default good: each one must be read, trusted, and kept in sync with code that keeps changing under it.

- **About to write a comment or docstring** → write it only if the *why* is non-obvious: a hidden constraint, a workaround, or behavior that would surprise a reader
  - _Because:_ if removing it wouldn't confuse a reader, it's just something to keep in sync
- **A comment explains *what* the code does** → make the code say it (better name, extracted function) and delete the comment
  - _Because:_ prose standing in for clarity drifts; code doesn't
- **Writing a docstring** → hold it to the same bar as a `#` comment
  - _Because:_ docstrings aren't exempt; the exception is a CLI usage docstring the script prints
- **About to note what changed or why you edited** → put it in the commit message
  - _Because:_ history belongs to version control; in the file it's stale by the next edit
  - ✗ `# Updated to use pathlib` ✓ no comment; the commit says it
