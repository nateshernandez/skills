# design.md format

A design fixes the shapes that are costly to change before tasks are planned. The requester approves it with the spec's contract in mind; the planner, the test author, the builders, and the code reviewer all work from it.

## When a spec needs one

- **A persistent data model** → new tables or documents, versioning, retention, ownership
- **A protocol between parts** → how agents, services, or processes talk: messages, order, failure
- **A state machine** → states, the moves between them, who may make each
- **A public contract** → an API, an event, or a file format others depend on
- **None of these** → no design.md; the plan covers the rest

## Where it lives

- **`specs/<id>/design.md`** → beside spec.md; written after the spec is approved, before the plan
- **Approval** → the requester approves it by setting `status: approved` in a reply; the planner starts after
- **After the build** → codify moves the shapes that outlive the spec to `docs/architecture/<topic>.md`, and `design.md` stays as the record of what was built

## Shape

- **Frontmatter** → `id` (matches the folder) and `status`: `draft` or `approved`
- **Title** → `# Design: <feature name>`
- **Intro** → one line under the title, ≤ 25 words, the shape in plain words
- **Sections, in this order, each only if it applies**
  - `## Data model` → types or a schema; fields, relations, how a record is versioned or retired
  - `## Interfaces` → exact names, inputs, and outputs the parts agree on
  - `## Flows` → a `mermaid` diagram per flow that crosses parts or time
  - `## Invariants` → required; the rules that always hold
- At least one of Data model, Interfaces, or Flows

## Invariants

- **Shape** → `- **5.I1 <situation>** → <rule that always holds>`, rule ≤ 20 words
- **ID** → `<spec number>.I<index>`, permanent once approved like a behavior's; retire and replace to change one
- **Test** → each invariant has one unit test titled with its ID; `check_coverage.py` fails one without
- **Good** → `5.I2 Version numbers` → `count up by one per document with no gaps`
- **Bad** → `5.I2 Versioning` → `works correctly`: nothing can fail it

## Limits

- ≤ 80 non-blank lines including code and diagrams
- Types and diagrams over prose; no paragraphs
- No file paths, libraries, or task order; plan.md owns those

## Using it

- **Planner** → names a task per shape, cuts tasks along Interfaces, and makes the first task the types and stubs
- **Test author** → writes the invariants' unit tests
- **Builders** → code against Interfaces exactly; a change to one is a blocked report, not an edit
- **Code reviewer** → blocks a diff that breaks an invariant or drifts from the Interfaces
