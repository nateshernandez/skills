# Spec format

A spec is the contract between the requester and the build team. The requester approves it in about two minutes; every agent after that works from it.

## Where it lives

- **`specs/<NNN>-<slug>/spec.md`** → the review card; the only file the requester must read
  - Created by kit's `new_spec.py <slug>`; NNN counts up, so it's creation order
- **`specs/<id>/screens/`** → images the spec shows under Looks like
- Everything else in `specs/<id>/` is agent-facing (see the build skill)

## Shape

- **Frontmatter** → `id` (matches the folder), `status`, `size`, optional `retired`
  - `status`: `draft` → `approved` → `building` → `verifying` → `done`, or `blocked`
  - `size`: `S` one task, no UI flow · `M` a screen or flow · `L` several screens; consider splitting
- **Title** → `# <Feature name>`
- **Outcome** → one line under the title, ≤ 25 words, what's true for the user
- **`## Decide`** → the guesses; `none` if the request settled everything
- **`## Behaviors`** → what the requester will observe; each becomes one acceptance test
- **`## Not doing`** → scope fence; `none` allowed
- **`## Looks like`** (optional) → images only, `![caption](screens/x.png)`

## Item shape

- **Decision** → `- **3.D1 <situation>** → <default>` plus exactly one `  - _Alt:_ <other option>`
  - No Alt means nothing was decided; move it to Behaviors
- **Behavior** → `- **3.B1 <situation>** → <observable outcome>`, optionally one `  - _Because:_`
  - Situation names a trigger or state; outcome names what someone sees or what's stored
  - ✗ `3.B3 Validation` → `works well` ✓ `3.B3 Visitor submits "abc"` → `inline error under the field; nothing saved`

## Numbering and IDs

- **Spec number** → creation order, not priority; pick what to build next from approved specs
- **Item ID** → `<spec number>.<D|B><index>`, like `3.D1` or `3.B4`; unique across all specs
- **In replies** → a bare `D1` is fine while one spec is under review; files always use full IDs
- **While `draft`** → IDs may change freely
- **Once approved** → an ID means one thing forever; `lint_spec.py` compares against the last committed approved version
  - Rewording an item → retire its ID and add a new one
  - Dropping an item → list its ID under `retired:` in the frontmatter, like `retired: 3.B2, 3.D1`
  - New IDs take the next number; retired numbers never come back
- **Everything that cites IDs** → tasks, tests, probes, findings, report; kit's `check_ids.py` flags stale ones

## Lenses

- **Product** → the outcome line, Not doing, and whether each behavior earns its place
- **Design** → Looks like; states the user sees (empty, loading, error, success)
- **UX** → error recovery, keyboard use, small screens, copy the user reads
- **Tech** → decisions the stack forces (storage, server vs client)
- **Quality** → every outcome is observable, so a test can check it
- **Security** → input, auth, abuse, data exposure; each risk becomes a behavior
- A lens that changes nothing leaves no trace in the spec

## Limits

- ≤ 50 non-blank lines, ≤ 5 decisions, ≤ 12 behaviors, ≤ 6 Not doing, ≤ 4 images
- Situation, outcome, Alt, Because: ≤ 20 words each
- No paragraphs, tables, code blocks, or `###` subsections
