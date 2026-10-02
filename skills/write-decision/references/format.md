# Decision record format

A decision record says what the system chose, why, and where the code is. A new engineer reads it in a minute and knows what future code must respect.

## Where it lives

- **`docs/decisions/<NNNN>-<slug>.md`** → one decision per file
  - Created by kit's `new_decision.py <slug>`; NNNN counts up, so it's creation order
  - Numbers never come back, even for superseded records

## When a record earns its place

- **Write one** → future code must follow the choice, and reversing it would touch many files
  - Examples: database and tenancy model, auth provider, money representation, telemetry pipeline
- **Skip it** → the choice is local to one file or easily reversed
  - A code comment or the build report's Decided without you covers it
- **Technical, with no code yet** → wait; it's written by the build that first implements it
- **Policy (retention, vendors, data use)** → `kind: policy`; no code needed

## Frontmatter

- **`id`** → matches the file name without `.md`
- **`kind`** → `technical` or `policy`
- **`status`** → `accepted` or `superseded`
- **`date`** → `YYYY-MM-DD` the record was accepted
- **`spec`** → the `specs/<id>` whose build introduced it, or `none`
- **`code`** → comma-separated paths from the repo root; required for `technical`
  - The files a reader should open first, not every file the change touched
  - Directories are fine; globs are not
- **`superseded_by`** → the replacing record's id; present exactly when `status: superseded`

## Body

- **Title** → `# <the decision as a fact>`: ✗ `Database choice` ✓ `Tenants share one Postgres, isolated by row-level security`
- **Context** → one line under the title: the force that made a choice necessary
- **`## Decision`** → what was chosen; ≤ 6 bullets
- **`## Why`** → the drivers; ≤ 5 bullets
- **`## Alternatives`** → ≥ 1 `- **<option>** → <why not>`; ≤ 4
- **`## Consequences`** → what future code must do, and the costs accepted; ≤ 6 bullets
- **`## Enforced by`** (optional) → `` - `<path>` → <what it checks> ``; the path must exist
  - A lint rule, a `.claude/rules/` file, a test, or a probe

## Permanence

- **Before merging to `main`** → edit freely; the requester reviews it in the build report
- **Accepted on `main`** → the body and title are frozen; the lint compares against `main`
  - Cited code moved → update `code:` only
  - The decision changed → write a new record, then set the old one's `status: superseded` and `superseded_by`

## Limits

- ≤ 40 non-blank lines after the frontmatter
- Every bullet ≤ 25 words
- No paragraphs, tables, code blocks, or `###` subsections
- How-to belongs in the code; the record says what and why
