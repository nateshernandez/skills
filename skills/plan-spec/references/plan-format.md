# plan.md format

Agent-facing: the builder and reviewers read it; the requester doesn't have to. Keep it ≤ 40 non-blank lines.

## Shape

```markdown
# Plan: <feature>

## Approach

- <how it works, one idea per bullet, ≤ 6 bullets>

## Files

- `src/app/waitlist/page.tsx` → server component rendering the form
- `src/app/waitlist/actions.ts` → server action: validate, rate-limit, store

## Risks

- **Email field → server action** → validate on the server, not just the client → B2
- **Anonymous POSTs to the action** → per-IP rate limit → B5
- **Emails stored in plain text** → acceptable for a waitlist → Flag

## Decisions

- **Action validates input with a schema before storing** → follows `docs/decisions/0002-input-validation.md`
- **Rate limits keyed by IP in Redis** → record: later public actions will reuse it

## Flags

- **Storage** → JSON file under `data/` until a database exists
```

## Decisions: what gets a record

- **`follows <record>`** → an accepted record in `docs/decisions/` this plan must respect
- **`record`** → a new choice later code must follow, costly to reverse; codified after review
  - Often a spec D item the requester approved, now with the code that implements it
- **Local or cheap to reverse** → leave it out; the report's Decided without you covers it
- **Plan contradicts an accepted record** → `supersedes <record>` plus a Flag, so the requester sees it
- `none` when the plan neither makes nor follows an architecture choice

## Threat checklist, per input or data path

- Who can reach it? Every endpoint, action, and handler is public, whatever the UI shows
- What does the server trust? Validate every field server-side
- What does it return? Only fields the UI needs
- What's secret? Server-only values never reach clients, logs, or error messages
- What can be abused? Repeats, large inputs, enumeration
- Each answer becomes a behavior already in the spec (cite its ID) or a Flag
