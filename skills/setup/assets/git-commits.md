<!-- always-on: commits aren't tied to any file type, so no path glob can load this -->

# Git commits

History is a straight line of short labels someone scans in `git log --oneline`, not a report of the session.

- **Writing the subject line** → imperative mood, ≤ 50 chars, no trailing period, no type prefix; name the change
  - _Because:_ a short subject stays readable when the log is scanned
  - ✗ `Updated the parser module to use pathlib and fixed edge cases` ✓ `Use pathlib in config parser`
- **Tempted to add a body** → only for a why the subject and diff can't show, in 1–3 lines; never files touched or checks run
  - _Because:_ git and CI already record what changed and what passed; repeating it buries the message
- **The subject needs "and" to cover the change set** → split it into separate commits
  - _Because:_ one commit per change keeps each subject short and each revert clean
- **Staging files** → `git add <paths>` by name; never `git add -A` or `git add .`
  - _Because:_ untracked scratch files and secrets end up in commits by accident
- **Choosing a branch** → commit on a feature branch, the session's if it names one; never directly on `main`
  - _Because:_ `main` changes only through reviewed pull requests
- **Bringing in changes from `main`** → rebase the branch onto `main`; never merge `main` into it
  - _Because:_ merge commits bend the history; a rebased branch lands as a straight line
- **Pushing during a build** → push when a task passes, a round ends, or the report is written; not mid-round
  - _Because:_ each push can rebuild a preview and start CI; an unpushed milestone risks at most one round's files
- **About to amend, rebase a pushed branch, force-push, or push** → ask first unless told to
  - _Because:_ these rewrite or publish history and are hard to undo
