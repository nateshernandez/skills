# Slide craft

What makes a slide readable from the back of the room. Layout mechanics (flow, pinning, the CSS subset) are in the Slides type's own `format.md`, `layout.md`, and `styles.md`, which an Artifact `read` of any Slides deck returns; this page is the judgment on top of them.

## The canvas

- **Margins** → 128px on every side; 160px at the bottom when a footer sits in the band at `bottom:64px`
  - _Because:_ a projector crops edges, and text near the edge reads as cramped
- **Text column** → sentences in a column 800–1000px wide; display lines up to 1500px
  - _Because:_ a line past about 60 characters makes the eye lose its place on the return
- **Vertical budget** → 824px inside the margins (792px with a footer); add up heights before writing
  - A heading is size × lines × 1.1; a table row is 2.1 × font size per line; a card is lines × size × line height + padding
  - _Because:_ nothing shrinks in kit's render; an over-full slide fails, so split it instead
- **Filling the height** → the evidence block takes `flex:1` under the heading and reaches at least 60% down the slide
  - _Because:_ a body that stops halfway reads as unfinished, and one pushed to the bottom leaves a hole under the title
- **Never** → `justify-content:center` or `space-between` on a content slide's column
  - _Because:_ either one moves the body away from its heading; statements and quotes may center

## Hierarchy

- **Type** → only the style's sizes; emphasis by weight, the accent, or italic, never a new size
  - _Because:_ four or five sizes used everywhere is what makes a deck look like one system
- **Reading order** → title, then the one element that proves it, then supporting labels
  - _Because:_ the audience spends the first 3 seconds on whatever is biggest and highest-contrast
- **The accent** → on the one thing per slide that proves the title: the bar, the number, the row, the word
  - _Because:_ signaling works only by contrast; two accents per slide cancel each other
- **Alignment** → left-aligned text on content slides; centered only on statement, quote, and section slides
  - _Because:_ a ragged left edge makes every line start in a new place
- **Rhythm** → every slide of a layout uses the same section style, gaps, and heading markup
  - _Because:_ headings that hop between slides read as careless; `render_deck.py` measures it

## Colour

- **Backgrounds** → the light background for content; the dark one for the cover and closing; the accent for at most one statement slide
  - _Because:_ a background change marks a moment; changing it often marks nothing
- **Contrast** → text 4.5:1 on its background, 3:1 at 44px and up; `render_deck.py` measures each text element
  - _Because:_ projectors wash colour out; a pair that passes on a laptop fails on the wall
- **Meaning** → colour never says it alone: the winning bar also says "+12%, over plan"
  - _Because:_ about 1 in 12 men can't tell red from green, and printouts are often greyscale
- **Decoration** → no gradients by default, no shadows on text, no rounded cards with a coloured left border
  - _Because:_ these are the look of generated slides; one consistent restraint reads as a designer's

## Charts

Gene Zelazny, *Say It With Charts*, and Cole Nussbaumer Knaflic, *Storytelling with Data*.

- **Choosing** → bars for comparing amounts; a line for change over time; a table when exact values matter
  - _Because:_ length along a common baseline is the comparison people read most accurately
- **Pies, donuts, 3D, dual axes** → never
  - _Because:_ angles and areas are judged badly, and 3D distorts every value it shows
- **Labels** → values on the bars and series names at line ends; no legend
  - _Because:_ a legend makes the eye travel back and forth, which Mayer's contiguity principle warns against
- **Ink** → no gridlines, borders, or axis lines the values don't need; bars start at zero
  - _Because:_ every mark that isn't data competes with the data; a cut axis exaggerates the difference
- **Order** → bars sorted by value unless the categories have their own order, like time
  - _Because:_ sorted bars make the ranking visible without reading a single number
- **Highlight** → the bar or line that proves the title in the accent, the rest in `line` or `muted`
  - _Because:_ the title says what to see; the colour shows where

## Tables

- **Size** → at most 6 rows by 5 columns on a presented slide; more becomes two slides or an appendix
  - _Because:_ a table past that is a document someone has to read while you talk
- **Numbers** → right-aligned, tabular figures, one unit per column stated in the header
  - _Because:_ aligned digits compare at a glance; mixed units force arithmetic

## Images and diagrams

- **Images** → only the requester's files or what the sources hold; full-bleed photos `object-fit:cover`, screenshots `contain` on a contrasting panel
  - _Because:_ stock photos of handshakes and lightbulbs say nothing and say it generically
- **Labels on images** → `<p>`s pinned over the image in a `position:relative` box, never text inside an SVG
  - _Because:_ fonts don't load inside SVGs, and the PowerPoint export can't reach that text
- **Diagrams** → at most 7 boxes, one reading direction, every arrow meaning the same thing
  - _Because:_ a diagram past 7 parts is a map to study, not evidence to glance at
- **Icons** → only beside the word they stand for, never as decoration
  - _Because:_ an icon alone is a guess the audience has to make
