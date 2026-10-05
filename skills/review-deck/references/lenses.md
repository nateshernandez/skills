# Lenses

Each deck review runs three reviewers in parallel, each in fresh context with only its lens's inputs. They write `decks/<id>/reviews/<lens>-r<round>.md`.

## story

- **Reads** → `storyline.md`, then each slide's heading and notes; not the screens
- **Checks**
  - The titles alone, in order, make the argument and reach the Ask
  - The answer or ask arrives by slide 3; the last slide restates it as a next step
  - Each content title is one claim; no title needs "and"
  - Support groups don't overlap, and together they cover the answer
  - Each body proves its own title; nothing proves a different slide's claim
  - The skeptic in `Audience:` gets their doubt answered somewhere
  - Pace: about one content slide per minute
- **Blocks on** → a gap in the argument, a slide that proves nothing, the ask missing or late

## design

- **Reads** → `screens/deck.png`, every `screens/<id>.png`, the style, `docs/deck/guide.md`; not the storyline
- **Checks**, against [../../build-slides/references/craft.md](../../build-slides/references/craft.md)
  - Glance test: each slide's point lands in about 3 seconds
  - The eye goes to the evidence that proves the title, and the accent marks only that
  - Slides of one layout look the same; headings never hop
  - Charts: right type, labels on the data, no legend, bars from zero, the proving bar highlighted
  - Tables: 6 rows by 5 columns at most, numbers right-aligned
  - Nothing crowded, nothing floating in empty space, nothing decorative
  - The deck as a whole: backgrounds change on purpose; the contact sheet has rhythm
- **Blocks on** → a slide that fails the glance test, a misleading chart, text you can't read at the back of the room

## copy

- **Reads** → each `slides/<id>.html`'s text and notes, and `docs/deck/voice.md`; never the storyline or the sources
  - _Because:_ the audience never sees the storyline; copy is judged as they meet it
- **Checks**, against [copy.md](copy.md)
  - Every claim specific: a number with its comparison, a name, an example
  - No tell from copy.md, including the ones the lint can't see
  - The cut pass: propose the words to remove, quoting them
  - Notes read aloud naturally, in the requester's voice
- **Blocks on** → a vague claim on a title, a generated-sounding title, notes that can't be spoken
- **Writing a finding** → quote the text and give the rewrite: `"Strong growth" → "Revenue grew 31%"`

## Findings

```markdown
---
lens: design
round: 1
verdict: fail
---

# Design review, round 1

- **[blocker] S4** → three bars share the accent; only Q3 proves the title
  - _Evidence:_ screens/revenue.png
- **[note] deck** → two dark slides in a row flatten the close
  - _Evidence:_ screens/deck.png
```

- **Ref** → the slide's S number, several as `S3, S5`, or `deck`
- **Severity** → `blocker` when the audience would misread, miss, or doubt the point; `note` otherwise
- **Evidence** → exactly one line: a screen, a quoted line from a slide file, or a storyline line
- **Limits** → 25 words a finding, 15 findings a file; `verdict: fail` exactly when there's a blocker; `none` when there are no findings
