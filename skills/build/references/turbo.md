# Turbo mode

Turbo builds a spec with fewer agents and one review round. It keeps the spec with its prototype, the approval, failing acceptance tests, the gates, the verifier, the security review, and the full gate. It cuts the planner, per-task builders, the code and UX lenses, re-review of fixes, and codify.

Everything the build skill says still holds, except where a rule here replaces it.

## Picking the mode

- **Resolving the mode** → `--turbo` or `--standard` in the request, else the spec's `mode:`, else `build.mode` in the config, else standard
  - _Because:_ a flag is the requester's latest word; the spec keeps the mode for a resumed build
- **Mode resolved** → write `mode: <mode>` into the spec's frontmatter before showing it for approval, or when setting `status: building`
  - _Because:_ the requester approves the mode with the spec, and `spec_status.py` reads it back
- **Turbo, and the config sets `build.turbo_model`** → pass it as the Agent tool's `model` for the test author, builders, and verifier; the security reviewer keeps the session's model
  - _Because:_ the security lens is the one turbo keeps because a miss costs most

## What turbo changes

- **Planning** → no planner and no plan.md; write tasks.json yourself: one `T1` covering every behavior, `base` from `git rev-parse HEAD`; `check_tasks.py` passes
  - _Because:_ this is the size S path at any size; one task needs no slicing
- **Building** → one builder for `T1`, whatever the size
  - _Because:_ cold starts and gates between tasks are where a standard build spends its time
- **Watching the builder** → judge a stall by its last tool call's age alone; a long total runtime is expected
  - _Because:_ one builder does the work of several, so passing 8 minutes is normal here
- **Choosing reviewers** → the verifier always; security-reviewer by the standard rule; never code-reviewer or ux-reviewer
  - _Because:_ the verifier proves behaviors in the running app; a security miss costs the most
- **Round 1 has blockers** → one `F1` task covering them all, one builder, then the full gate; no round 2
  - _Because:_ the fix is held to the gate and to the probes that found each blocker
- **`F1` reports blocked, or the full gate is still red after its one fix** → set `status: blocked`; report each ✗ with one question
  - _Because:_ turbo has no later round to converge in
- **Checking Done When** → round 1's `fail` verdicts count as answered once `F1` passes and the full gate is green
  - _Because:_ no round 2 runs to write `pass` verdicts
- **Codify** → skip it; Codified is `none`
  - _Because:_ records describe reviewed code, and nobody reviewed this code's architecture
- **Showing the report** → say `/kit:build <id> --standard` runs the skipped reviews before merge
  - _Because:_ the requester can buy back the cut lenses without rebuilding

## Report

A turbo report has a `## Skipped` section between Open notes and Try it; `lint_outputs.py` requires it for a turbo spec and rejects it for a standard one. List each step this build skipped:

```markdown
## Skipped

- **Planner** → no threat model or plan Decisions
- **Per-task builds** → one builder and one commit for every behavior
- **Code review** → idioms, type holes, test levels, decision records, and the architecture guide's homes unchecked beyond the gate
- **UX review** → screens, states, accessibility, and the design guide unchecked
- **Fix re-review** → F1 passed the gate and its probes; no reviewer saw it
- **Codify** → no decision records, rules, or design and architecture guide updates
```

- Leave out UX review when the standard rules wouldn't have run it either: no UI change, or no `screenshots` in the config
- Leave out Fix re-review when round 1 had no blockers

## Upgrading to standard

- **A turbo spec is resumed with `--standard`** → set `mode: standard` and `status: building`; run round 2 with every reviewer the standard rules choose, then the standard loop to round 3, codify, and a new report
  - _Because:_ the files already hold round 1, so only the skipped lenses' work is new
