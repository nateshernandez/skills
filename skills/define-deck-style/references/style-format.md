# Deck style format

A project's deck style is three files in `docs/deck/`. What a script can check goes in `style.json`; what takes judgment goes in `guide.md`; how the words should sound goes in `voice.md`. A deck may carry its own `decks/<id>/style.json`, which replaces the house one for that deck only.

## Where it lives

- **`docs/deck/brand/`** → the requester's inputs: brand guide, logos, colour sheets, past decks, writing samples
- **`docs/deck/style.json`** → fonts, colours, sizes, title rules, banned phrases; `lint_deck.py` and `render_deck.py` enforce it
- **`docs/deck/guide.md`** → house rules in kit's rule format, read by slide-builder and the reviewers
- **`docs/deck/voice.md`** → the requester's voice, with quoted examples, read by slide-builder and the copy reviewer
- **`docs/deck/assets/`** → logos and images every deck may copy into its own `assets/`

## style.json

```json
{
  "kind": "presented",
  "fonts": {
    "heading": { "family": "Source Serif 4", "href": "https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600&display=swap" },
    "body": { "family": "Public Sans", "href": "https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;700&display=swap" }
  },
  "colors": { "background": "#f6f4ef", "surface": "#ebe7df", "line": "#d6d0c4", "text": "#1c2230", "muted": "#535c6b", "accent": "#b33f0b" },
  "sizes": { "number": 180, "display": 96, "title": 60, "body": 32, "small": 24 },
  "titles": { "case": "sentence", "max_words": 15 },
  "banned": ["world-class", "solution"]
}
```

- **`kind`** → `presented` or `read`; the default for decks whose storyline doesn't set one
- **`fonts`** → `heading` and `body` required, any other role allowed; each `{family, href}`
  - `href` is a `https://fonts.googleapis.com/css2?…` link; leave it out for a basic face every computer has, like Georgia or Arial
  - At most 3 families
- **`colors`** → `background`, `text`, `muted`, and `accent` required, any other name allowed; `#rrggbb` only
  - Every opaque colour on a slide must be one of these, so add `surface` and `line` if cards and rules need them
  - Translucent colours, like an `rgba(…, .55)` scrim, are always allowed
- **`sizes`** → `title`, `body`, and `small` required; `display` and `number` used by statement and big-number slides when present
  - At most 5 sizes, none under 24px; every text element on a slide must use one
- **`titles.case`** → `sentence`, `title`, or `any`
- **`titles.max_words`** → 4 to 25; 15 when left out
- **`banned`** → phrases this requester never wants, added to kit's own list

## Choosing values

- **Brand colours given** → map them to roles: the darkest neutral is `text`, the lightest is `background`, one brand colour is `accent`
  - _Because:_ a brand palette is for logos and marketing; a deck needs roles, and usually just one accent
- **Pairs to check** → text, muted, and accent on background and surface: 4.5:1; background on text and accent: 4.5:1
  - _Because:_ those are the pairs slides put text in; `render_deck.py` fails any that falls short
- **A brand colour fails contrast as text** → keep it for fills and bars; darken a copy for text and name it `accent-text`
  - _Because:_ the brand colour still shows; the words on it stay readable on a projector
- **Brand font isn't on Google Fonts** → the closest Google family, named in guide.md as a stand-in
  - _Because:_ Slides loads web fonts by link; a missing font silently falls back and breaks the layout
- **No brand** → the starter style, with one accent chosen for the audience
  - _Because:_ a restrained default beats a generated "brand" nobody asked for

## guide.md

Rules in kit's format, one per house convention the requester states or the brand guide sets, such as:

- **Every slide** → the logo at small size in the footer band, right-aligned
- **Customer names** → only those in `docs/deck/brand/approved-logos.md`
- **Confidential decks** → "Confidential" in the footer band on every slide

Each rule says the situation, what to do, and a `_Because:_`. Rules a script can check belong in style.json instead.

## voice.md

- **How they sound** → 3–6 bullets: sentence length, person (we or I), formality, how they open and close
- **Words they use** → their terms for their product, customers, and metrics
- **Words they avoid** → added to `banned` in style.json as well
- **Examples** → 3–5 sentences quoted from the samples, each with its source file
