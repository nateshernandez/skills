# market.md format

`docs/product/market.md` is the evidence the brief stands on. The brief's `sourced` and `inferred` claims cite its M IDs; the product reviewer opens its links. `lint_product.py` checks the shape. Keep it to 150 non-blank lines.

## Shape

```markdown
---
researched: 2026-10-03
---

# Market

Solo bookkeepers chase client documents every month; capture tools exist but need clients to adopt an app.

## Sources

- **M1 r/Bookkeeping thread: receipts from clients "still a nightmare", 69 comments** → https://www.reddit.com/r/Bookkeeping/comments/1run75a/
- **M2 r/Bookkeeping: 22 posts in 12 months on chasing clients; 2 with 20+ comments, most by builders** → https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=Bookkeeping&query=chasing+clients&after=2025-10-08
- **M3 Acme pricing page: $20 a month per client, read 2026-10-03** → https://acme.example/pricing

## Competitors

- **Acme** → receipt capture for accountants; $20 a month per client; clients must install its app (M3, M1)

## Alternatives

- **Email and text reminders** → bookkeepers nag by hand at month-end (M1, M2)

## Failed attempts

none

## Demand

- **Engaged threads are rare** → one thread with 69 comments; the rest are survey posts by builders (M1, M2)

## Complaints

- **Client adoption** → "clients won't log into a new portal" repeats across threads (M1)

## Unknown

- Whether bookkeepers pay for chasing alone; ask in interviews
```

## Rules

- **Frontmatter** → `researched:` the date the research ran
- **Summary** → one line under `# Market`: the market in plain words
- **Sources** → `- **M<n> <what the source shows>** → <link>`; one per page or rerunnable query; numbers only go up
  - A Reddit count's link is the `cite:` URL reddit_search.py prints
  - Paywalled or estimated figures say so in the bold part: "estimate", "paywalled"
- **Competitors, Alternatives, Failed attempts, Demand, Complaints** → `- **<name>** → <what's true> (M1, M4)`, ending with its sources in brackets
  - `none` when the search found nothing, except Competitors: the leader or the nearest substitute is always one
- **Competitor items** → who it's for, its price, its traction signals, and its customers' top complaint, or "no complaints found"
- **Failed attempts items** → what it was, when it stopped, and the reason it gave or others gave
- **Unknown** → plain bullets: what research couldn't settle, and how to find out; `none` allowed
- **Quotes** → 25 words or fewer, in quotation marks, never with a username; the lint checks both
- **Not allowed** → tables, code blocks, `###` subsections
