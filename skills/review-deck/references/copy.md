# Copy

How the words on slides and in notes should read: like a specific person who knows the material, not like text generated about it. `lint_deck.py` catches the mechanical tells; the copy reviewer catches the rest. A project's `docs/deck/voice.md` adds the requester's own voice on top, and wins where they differ.

## What generated text does

Generated text drifts toward the most probable sentence, which is the most generic one. Its tells come from three habits:

- **Vagueness** → claims without a number, a name, or an example; "significant growth", "key stakeholders"
- **Borrowed drama** → setups and reveals that make an ordinary point sound like an insight
- **Uniform shape** → every bullet the same length, every list three items, every paragraph closing on a summary

## Rules

- **Writing a claim** → put the number, the name, or the example in it
  - ✗ `Strong growth across key segments` ✓ `Enterprise revenue grew 31%; SMB was flat`
  - _Because:_ a specific claim can be checked, so it's believed; a vague one can't, so it's skimmed
- **A number** → with its unit, its period, and what it's compared against
  - ✗ `Churn improved` ✓ `Monthly churn fell from 3.1% to 2.4% since June`
  - _Because:_ a bare number makes the audience guess whether it's good
- **Choosing a word** → the plain one: use, help, show, start, cut, about
  - ✗ `leverage`, `facilitate`, `demonstrate`, `commence`, `reduce costs by approximately` ✓ `use`, `help`, `show`, `start`, `cut costs by about`
  - _Because:_ fancy words slow reading and signal padding
- **A sentence has a doer** → name it, in active voice
  - ✗ `Mistakes were made in onboarding` ✓ `Onboarding lost 40% of trials at the billing step`
  - _Because:_ passive voice hides who acts, which is usually the point of the slide
- **Hedges and intensifiers** → cut very, really, actually, quite, truly, incredibly, significantly
  - _Because:_ they add length and subtract confidence
- **Items in a list** → the same grammar for each, and as many as there are; two and four are fine
  - _Because:_ a list padded to three is the most common rhythm of generated text
- **Signposting** → cut "Here's why", "Let's look at", "It's important to note", "The key takeaway is"
  - _Because:_ the slide's title already says what's coming; signposts delay it
- **Ending a slide or note** → stop when the point is made; no recap of what was just said
  - _Because:_ a summary of three lines the audience just read treats them as forgetful
- **Jargon and acronyms** → spell out on first use, or replace with what it means to this audience
  - _Because:_ an acronym the room doesn't share loses them for the rest of the slide
- **Numerals** → digits for every number, `%` not "percent"
  - _Because:_ digits are faster to read and stand out on a slide

## Tells the lint catches

Each phrase below fails `lint_deck.py` in titles, slide text, and notes. A style's `banned` list adds the requester's own.

- **Inflated words** → delve, unlock, unleash, seamless, leverage, robust, cutting-edge, game-changing, revolutionary, transformative, synergy, holistic, empower, elevate, landscape, journey, tapestry, realm, paradigm, supercharge, next-level, world-class, best-in-class, innovative, harness, foster, streamline, testament, pivotal, crucial, embark, vibrant, meticulous, ever-evolving, fast-paced
- **Stock phrases** → in today's, the power of, at the end of the day, let's dive, dive into, deep dive, key takeaways, in conclusion, furthermore, moreover, it's worth noting, the magic, secret sauce, here's the thing, the future of
- **`It's not X, it's Y`** and **`not just X, but Y`** → state what it is
- **Emoji** and **exclamation marks** → words carry the meaning; evidence carries the energy
- **Titles** → questions, dashes, lists of three, Title Case where the style wants sentence case
- **`Label:` lead-ins** → `<b>Speed:</b> faster builds` becomes `Builds finish in half the time`
- **Em dashes** → more than one in a slide's text; use a period

## Tells the reviewer catches

- **Faux insight** → a title that names a concept instead of a finding: `The trust gap`, `The magic moment`
- **Symmetry** → bullets of identical length and rhythm, or parallel pairs that sound like a slogan
- **Abstraction** → a slide that could appear in any company's deck unchanged
- **Hedged both ways** → "while X is true, Y also matters" with no position taken
- **Restated title** → body text that repeats the title in other words instead of proving it
- **Unspeakable notes** → read the notes aloud; a sentence you'd never say gets rewritten as you'd say it

## The cut pass

- **Every slide** → try removing each word, then each line; keep what the claim needs
  - _Because:_ a first draft runs about 30% long; the audience pays for every extra word
