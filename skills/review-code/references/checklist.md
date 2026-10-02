# Code checklist

The project's own checklist, `.claude/kit/checklists/code.md`, adds framework and stack checks to this one.

## Decisions and rules

- The diff follows every record plan.md's Decisions names, and any other record whose `code:` it touches
- The diff follows every `.claude/rules/` file whose `paths:` match the files it changed
- `check_decisions.py` passes: no record cites code the diff moved or deleted

## Framework

- Each framework API is used the way its installed docs describe, not the way an older version did
- Work happens where the framework expects it (server or client, request or background)

## Types and errors

- No `any`, casts that hide a mismatch, or type and lint suppressions
- Errors the user can cause are shown to the user; others fail loudly

## Simplicity

- No dead code, unused exports, or speculative options
- No abstraction with a single use
- Names say what things are, in the spec's words

## Tests

- Every logic branch is run by some test: unit, acceptance, or probe
- Unit tests where logic is pure and cheap to test; missing ones are notes when another test covers the branch
- Tests assert behavior, not implementation details
- No test was weakened to pass
