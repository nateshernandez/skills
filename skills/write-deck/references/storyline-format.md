# Storyline format

A storyline is a deck's spec: the argument as one sentence per slide, which the requester approves before any slide is built. It's a ghost deck, the consultants' name for a deck's titles written out before any slide is designed.

## Where it lives

- **`decks/<NNN>-<slug>/storyline.md`** → the review card; created by `new_deck.py <slug>`
- **`decks/<id>/screens/wireframes.png`** → every slide as a grey wireframe with its real title, from `render_deck.py --wireframes`
- **`decks/<id>/slides/<id>.html`** → one Slides-format `<section>` per slide, built after approval
- **`decks/<id>/assets/`** → images and logos the slides use; `src="assets/<file>"`
- **`decks/<id>/reviews/<lens>-r<n>.md`** → story, design, and copy findings
- **`decks/<id>/published.json`** → the Slides artifact's URL and uploaded images; written by `publish_deck.py`
- **`decks/<id>/style.json`** → only when this deck's look differs from `docs/deck/style.json`

## Shape

- **Frontmatter** → `id` (the folder), `status` (`draft` → `approved`), `kind`, `minutes`
  - `kind`: `presented` (someone talks over it) or `read` (sent ahead, read alone); the style's `kind` when left out
  - `minutes`: the talk's length; required for `presented`
- **Title** → `# <Deck title>`, which becomes the cover's title
- **`Audience:`** → one line, ≤ 25 words: who's in the room, what they know, what they doubt
- **`Ask:`** → one line, ≤ 25 words: what they decide, do, or believe at the end
- **`## Decide`** → open choices, as in a spec: `- **D1 <situation>** → <default>` and one `_Alt:_`; ≤ 5, or `none`
- **`## Slides`** → the deck in order, one item per slide
- **`## Not saying`** → ≤ 6 bullets, true things left out on purpose; or `none`
- **`## Sources`** → each file or link the evidence comes from, and what it supplies; or `none`, and every figure is a `[__]` placeholder
- **`## Looks like`** → `![Wireframes](screens/wireframes.png)`, later `![Deck](screens/deck.png)`

## Slide items

```markdown
- **S3 revenue · chart** → Revenue beat plan for the third straight quarter
  - _Shows:_ bars of quarterly revenue against plan, Q1 to Q3, from finance.xlsx
```

- **`S3`** → the slide's number; replies cite it ("S3: use a table"); it stays when slides move
- **`revenue`** → the slide's id and file name, `[A-Za-z0-9_-]`
- **`chart`** → one of the layouts in [../../build-slides/references/layouts.md](../../build-slides/references/layouts.md)
- **The title** → becomes the slide's heading word for word; `lint_deck.py` compares them
- **`_Shows:_`** → ≤ 20 words: the evidence the slide puts on screen, and its source; required on content layouts

## Numbering

- **New slide** → the next unused number, wherever it lands in the order
- **Moved slide** → keeps its number; the list order is the deck order
- **Cut slide** → its number isn't reused, so old review findings still point at nothing new

## Limits

`lint_deck.py` checks each of these:

- **Slides** → ≤ 40, and ≤ 1.5 content slides per minute of a presented talk
- **Layouts** → the first slide is `title`; no layout more than 3 times in a row; `points` on at most a quarter of content slides
- **Titles** → ≤ the style's `max_words` (15 unless set); content titles ≥ 4 words, a claim not a label; no question marks, dashes, or lists of three; the style's case
- **Copy** → no phrase from [../../review-deck/references/copy.md](../../review-deck/references/copy.md)'s list
