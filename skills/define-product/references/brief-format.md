# Brief format

`docs/product/brief.md` is the product's contract: what it is, for whom, why it can win, and what's still a guess. The requester approves it by replying by ID, as with a spec. Every later spec, design system, and architecture reads it. `lint_product.py` checks everything below, on each write once kit is set up.

## Where it lives

- **`docs/product/brief.md`** → the card the requester approves; copied from assets/brief-template.md
- **`docs/product/market.md`** → the evidence: sources with links, competitors, complaints (../../research-market/references/market-format.md)
- **`docs/product/reviews/product-r<n>.md`** → the product reviewer's findings per round (below)
- **`docs/product/validation.md`** → interview plan, smoke tests, and results (validation.md)

## Frontmatter

- **`status`** → `draft` until the requester approves, then `approved`
- **`ambition`** → `venture`, `bootstrapped`, or `indie`; it sets the bar for Size and Model (business-basics.md)
- **`verdict`** → `pending` while drafting; then `go`, `narrow`, `pivot`, or `stop`
- **`retired`** → optional; PD, PA, or PF IDs dropped after approval, like `retired: PA3, PD1`

## Body

- **Title** → `# <Product name>`, then one pitch line of 25 words or fewer
- **Claim sections, in order** → Customer, Problem, Alternatives, Solution, Why now, Market, Model, Channels, Edge, Why you
  - 1 to 3 items each: `- **<topic>** → <claim>` with exactly one `  - _Evidence:_` line
  - What each section must answer is in business-basics.md
- **`## Decide`** → choices research left open: `- **PD1 <choice>** → <default>` with one `  - _Alt:_`; `none` allowed; at most 5
- **`## Assumptions`** → riskiest first: `- **PA1 <belief>** → untested | holds | fails` with one `  - _Test:_`; 1 to 8
- **`## Verdict`** → leave it out while `verdict: pending`; then all seven dimensions, below
- **`## First version`** → needed when the verdict is `go` or `narrow`: `- **PF1 <feature request>** → tests PA1, PA3`; at most 8
- **`## Not doing`** → plain bullets; `none` allowed; at most 6
- **`## Words`** → optional glossary for module names: `- **<noun>** → <meaning>`; at most 12
- **Limits** → 100 non-blank lines; bold parts up to 20 words, text after `→` up to 40, nested lines up to 25
- **Not allowed** → tables, code blocks, `###` subsections, paragraphs

## Evidence grades

- **`sourced M2, M5`** → the claim is what those market.md sources say, nearly word for word
- **`inferred M1, M3`** → reasoning from those sources; a reader can check the step
- **`assumed PA2`** → no evidence yet; PA2 holds the test that will settle it
- **`validated PA2`** → PA2's test ran and it `holds`; the result is in validation.md
- **`stated`** → the requester's own word, used for Why you and what only they know
- **Choosing** → the weakest grade that's true; an honest `assumed` beats a stretched `inferred`

## Verdict

- **Dimensions** → Pain, Reach, Willingness to pay, Gap, Edge, Why you, Size, each once
- **Item** → `- **Pain** → <rating>: <why, citing brief items or M IDs>`
- **Ratings** → `strong`, `mixed`, `weak`, or `unknown`; unknown means research found nothing either way
- **`go`** → no dimension weak; the first version tests the riskiest unknowns
- **`narrow`** → worth building for a smaller customer group or a smaller problem than the pitch names
- **`pivot`** → the evidence points at a different customer or problem; say which in the pitch of a new draft
- **`stop`** → pain or willingness to pay is weak and no test could change that cheaply

## IDs

- **Kinds** → `PD` decisions, `PA` assumptions, `PF` first-version features; claims carry no IDs
- **While `draft`** → IDs may change freely
- **Once approved** → an ID's bold part never changes; an assumption's status after `→` may
  - Rewording or dropping one → list it under `retired:`, then add a new ID numbered above every used one
- **Who cites them** → validation results, review findings, and the requests that start each `/kit:build`

## Review findings

`docs/product/reviews/product-r<n>.md`, linted like a build review's findings:

```markdown
---
lens: product
round: 1
verdict: fail
---

# Product review, round 1

- **[blocker] PA3** → no source shows anyone paying for chasing alone; the two leaders bundle it
  - _Evidence:_ M3, M4
- **[note] Edge** → texting is easy to copy; name what compounds
  - _Evidence:_ brief.md Edge
```

- **Ref** → the PD, PA, or PF ID, or the claim section's name
- **Severity** → `blocker` when the brief can't survive the question as written; `note` otherwise
- **Evidence** → exactly one line: M IDs, a link, or the brief line it rests on
- **Limits** → 25 words a finding, 15 findings a file; `verdict: fail` exactly when there's a blocker; `none` when there are no findings
