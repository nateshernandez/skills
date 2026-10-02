# Build artifacts

Everything a build leaves behind lives in `specs/<id>/`. Only `spec.md` and `report.md` are for the requester; the rest is agent memory, committed so any session can resume.

## Files

- **`spec.md`** → the approved contract (write-spec)
- **`plan.md`** → approach, files, risks; planner writes it (plan-spec)
- **`tasks.json`** → ordered tasks; only `mark_task.py` flips `passes`
- **`progress.md`** → append-only log, one line per builder run
- **`reviews/<lens>-r<round>.md`** → findings per lens per round
- **`report.md`** → the delivery report the requester reads
- **`screens/`** → prototype and review screenshots
- Acceptance tests and probes live where `.claude/kit/config.json` says: `tests.acceptance` and `tests.probes`
- Probe titles start with `<n>.B<k>` (a behavior) or `<n>.outcome` (the whole-feature check, `<n>.outcome probe: ...`)
  - Kept probes don't print (`console.log`); `lint_outputs.py` checks both when a probe is written
  - The task gate skips `<n>.outcome` probes; the full gate runs them

## During review

- The orchestrator runs `review_app.py start` before the round and `review_app.py stop` after it
  - It runs `app.serve` in the background and returns `READY <url>` once `app.url` answers
  - Without an `app` in the config it does nothing; reviewers' test runs start what they need
- Reviewers run tests with `run_tests.py <id> [file ...]`, which sets `app.env` and `KIT_APP_URL`
- Reviewers capture screens with `screens.py specs/<id>/screens/r<n> <route> ...`
- Reviewers never start, stop, or rebuild the app; the builder's gate already built it
- The app doesn't answer → report "review app broken" and stop
- Reviewers never run the gate or the full `check`; the builder's gate already did

## tasks.json

```json
{
  "spec": "001-waitlist",
  "base": "<commit sha before the first task>",
  "tasks": [
    { "id": "T1", "title": "Waitlist form with validation", "covers": ["1.B1", "1.B2"], "passes": false },
    { "id": "F1", "title": "Fix: error shows before submit", "covers": ["1.B2"], "passes": false }
  ]
}
```

- `T<n>` tasks come from the plan; `F<n>` fix tasks come from blocker findings
- `covers` lists behavior IDs; empty only for fixes with no behavior (code findings, outcome blockers)

## progress.md

```markdown
# Progress

- **T1** → form and validation done; server action stores email
- **T2** → blocked: acceptance test 1.B3 expects a toast, spec says inline message
```

## Findings: reviews/<lens>-r<round>.md

```markdown
---
lens: ux
round: 1
verdict: fail
---

# UX review, round 1

- **[blocker] 1.B2 · src/app/waitlist/form.tsx:40** → error appears on blur, before the visitor submits
  - _Evidence:_ screens/r1-b2-blur.png
- **[note] 1.B4** → submit button is 36px tall; 44px is easier to tap
  - _Evidence:_ screens/r1-waitlist-mobile.png
```

- `lens`: `quality`, `ux`, `security`, or `code`
- Severity: `blocker` breaks a behavior or the lens's bar, or contradicts the spec's behavior text even when an acceptance test passes; `note` is everything else
  - The outcome probe's blocker has ref `outcome` and becomes a fix task with empty `covers`
- Caps the lint enforces: 25 words per finding, 15 findings per file
- `verdict: fail` exactly when there is a blocker
- Each finding has exactly one Evidence: a screenshot, failing test, command output, or `file:line`
- A probe quoted in Evidence is the test title exactly (it may end in `...`); the lint checks it against the spec's probe files
- No findings → the list is the single line `none`

## Codify

After the latest round passes and before the report, turn what the build settled into context for later builds.

- **Each entry under plan.md's Decisions marked `record`** → write it with write-decision, citing this build's code
  - _Because:_ written against reviewed code, a record describes the architecture that exists, not a guess
- **A pattern the diff set that later code must repeat** → propose it as a rule (write-rule), or a lint config change
  - _Because:_ rules come from code that exists, so they match the architecture instead of predicting it
- **A second feature reuses a UI piece the first one built** → move it to the shared components, with a section in the design guide and a gallery page
  - _Because:_ the third feature then finds it in the guide instead of building its own
- **A pattern appears once and nothing else must follow it** → no rule
  - _Because:_ every rule loads into later sessions; one-off rules are noise
- **Records and rules written** → commit them together; list each under the report's Codified
  - _Because:_ they steer every later build, so the requester confirms them alongside the code
- **Requester objects to one** → revise it on the branch before merge
  - _Because:_ records freeze once on `main`; until then they're drafts

## report.md

- Copy `assets/report-template.md`
- Every spec behavior appears once under Behaviors: `✓` when its acceptance test passes, `✗` with why when not
- Blocked on → open blocker findings, each with one question; only when `status: blocked`
- Decided without you → choices made after approval, each with a Because
- Codified → each decision record and rule this build wrote, for the requester to confirm; `none` if empty
- Open notes → `note` findings still open; `none` if empty
