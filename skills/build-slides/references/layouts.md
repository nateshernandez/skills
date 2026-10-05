# Layouts

Every slide names one layout in the storyline. Slides of one layout share the same markup, so the heading sits in the same place and the deck reads as designed rather than assembled. Examples use the starter style (`define-deck-style/assets/style.json`); use the deck's own style values.

## The shell every content slide shares

```html
<section id="revenue" style="background:#f6f4ef;color:#1c2230;font-family:'Public Sans', Arial, sans-serif;font-size:32px;padding:128px;display:flex;flex-direction:column;gap:64px">
<h2 style="font-family:'Source Serif 4', Georgia, serif;font-size:60px;font-weight:600;line-height:1.1;max-width:1500px">Revenue beat plan for the third straight quarter</h2>
<div style="flex:1;display:flex;flex-direction:column;gap:32px"><!-- the evidence --></div>
<aside>What you'll say over this slide, in full sentences. End with the bridge to the next one.</aside>
</section>
```

- **Heading** → the storyline title word for word, an `<h2>` at the top margin; never centered with the body
- **Body** → one evidence block with `flex:1`, so it fills the height under the heading; open space low on a slide is fine, a gap under the heading isn't
- **Source line** → a footer: `<p style="position:absolute;left:128px;bottom:64px;font-size:24px;color:#535c6b">Source: finance, Q3 close</p>`, and the section's padding becomes `128px 128px 160px`
- **Notes** → `<aside>` last; plain text; what the presenter says

## Word caps

The most words a presented slide's body may hold, title and notes not counted; a read deck may hold 2.5 times as many. `lint_deck.py` enforces them.

- `title` 20 · `section` 12 · `statement` 20 · `big-number` 20 · `chart` 25 · `diagram` 30
- `comparison` 45 · `table` 60 · `image` 15 · `quote` 45 · `points` 30 · `timeline` 40 · `closing` 25

## title

- **When** → the cover; always the first slide
- **Shape** → dark background, `<h1>` at the display size, one line under it: presenter and date, or the occasion

```html
<section id="cover" style="background:#1c2230;color:#f6f4ef;font-family:'Public Sans', Arial, sans-serif;padding:128px;display:flex;flex-direction:column;justify-content:flex-end;gap:32px">
<h1 style="font-family:'Source Serif 4', Georgia, serif;font-size:96px;font-weight:600;line-height:1.05;max-width:1500px">Q3 board update</h1>
<p style="font-size:32px;color:#f6f4ef">Dana Ruiz · October 2026</p>
<aside>…</aside>
</section>
```

## section

- **When** → opening each group of support, in decks with 3+ groups and 10+ slides
- **Shape** → the accent or dark background; the group's claim at the display size; nothing else

## statement

- **When** → the answer slide, or the one sentence the audience must remember
- **Shape** → centered column, the claim at the display size, an optional one-line qualifier; the deck's one accent-background slide is often this one

```html
<section id="answer" style="background:#b33f0b;color:#f6f4ef;font-family:'Public Sans', Arial, sans-serif;padding:128px;display:flex;flex-direction:column;justify-content:center;gap:32px">
<h2 style="font-family:'Source Serif 4', Georgia, serif;font-size:96px;font-weight:600;line-height:1.05;max-width:1500px">We need two senior hires to hold the Q1 launch</h2>
<aside>…</aside>
</section>
```

## big-number

- **When** → one figure is the evidence
- **Shape** → the number at the style's `number` size with `line-height:1`, a caption at body size saying what it counts and against what; at most three numbers in a row of equal tiles

```html
<div style="display:flex;flex-direction:column;gap:8px">
<p style="font-size:180px;font-weight:700;line-height:1;color:#b33f0b">41%</p>
<p style="font-size:32px;color:#535c6b">faster ramp for hires with a mentor, n=212</p>
</div>
```

## chart

- **When** → quantities over time or across groups
- **Shape** → bars on one baseline, the value above each, the label below; the bar that proves the title in the accent, the rest muted; labels are `<p>`s, never `<text>` in an SVG
- **Bars** → a fixed-height track with `align-items:flex-end`; each bar's height is its value times one scale for the slide

```html
<div style="flex:1;display:flex;gap:48px;align-items:flex-end">
<div style="flex:1;display:flex;flex-direction:column;justify-content:flex-end;gap:12px">
<p style="font-size:32px;font-weight:600">$4.1M</p>
<div style="height:300px;background:#d6d0c4"></div>
<p style="font-size:24px;color:#535c6b">Q1</p>
</div>
<!-- one column per bar; the highlighted bar's fill is #b33f0b -->
</div>
```

- **Lines, areas, scatter** → an `<svg aria-label="…">` with no `<text>`, inside a `position:relative` div; labels pinned over it as `<p>`s

## diagram

- **When** → how parts connect: a process, a system, a decision
- **Shape** → at most 7 boxes, read left to right or top to bottom; boxes are painted `<div>`s, arrows are `<x-shape kind="arrow-right">` between them

## comparison

- **When** → two or three options, before and after, us and them
- **Shape** → equal columns in one flex row (`flex:1` each); each column a `<h3>` and 1–3 short lines; the winner marked in words and the accent, never by color alone

## table

- **When** → many attributes across a few items
- **Shape** → at most 6 rows and 5 columns presented; numbers right-aligned with `font-variant-numeric:tabular-nums`; the row that proves the title on a `surface` background
- **Height** → a row is about 2.1 × the font size per line; 6 rows at 32px is about 400px

## image

- **When** → the thing itself: a product screen, a place, a person, the requester's own photo
- **Shape** → full-bleed `<img>` listed first, `object-fit:cover`, title on a scrim; or the image beside a 1–2 line caption
- **Only** → images the requester gave or the sources hold; never stock clichés or decorative pictures

## quote

- **When** → a customer's or expert's own words are the evidence
- **Shape** → the quote in italic at the body size, or the title size if it's under 15 words, with a 6–8px accent rule on its left; attribution under it at small size: name, role, and source

## points

- **When** → the evidence really is a short list nothing else fits; at most a quarter of content slides
- **Shape** → 2–4 lines, each one sentence, parallel grammar; no nested lists, no `Label:` lead-ins; a row of cards often reads better than a `<ul>`

## timeline

- **When** → steps or milestones in time
- **Shape** → 3–5 equal columns along one rule: date in the accent, one line under it

## closing

- **When** → the last slide
- **Shape** → dark background like the cover; the ask as a concrete next step with an owner or date; never "Thank you" or "Questions?"
