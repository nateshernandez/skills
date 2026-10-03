# Researching the look on Mobbin

The look comes from measuring real screens, not from adjectives. Mobbin's connector gives three searches. Each one returns low-resolution previews for you to read and a `mobbin_url` to cite.

- **`search_screens`** → one screen: "Linear issue list grouped by status", "Stripe customer detail with payments table"
- **`search_flows`** → a journey across screens: "Notion onboarding with workspace setup", "Vercel sign up with GitHub"
- **`search_sections`** → a marketing-site section: "pricing page with plan comparison table"

## What to search

- **The apps the requester named** → their main list, a detail page, a form or settings page, and sign-in, in light and dark when both exist
- **The product type** → two or three leaders the requester didn't name, so the look isn't one app's copy: "invoice list in a finance app", "dense issue tracker list"
- **Each core screen the second spec builds** → list, detail, form, settings, empty state, delete confirm, notice
- **Platform** → `web` for a web app, `ios` for an iPhone app; never mixed in one look
- **Queries** → describe one screen and what's on it; no style words ("modern", "clean"), no negations, one intent per query
- **How many** → 10 to 20 screens in all; stop once new screens stop changing a token

## Reading a screen

Look at each returned image itself; never describe a screen from its metadata.

- **Tones** → sidebar, content, card, and band, light and dark; the step between them (often 3 to 4% lightness)
- **Borders** → hairline or none; row dividers or whitespace
- **Accent** → which one hue, and where it appears: often only the primary button, links, and focus
- **Type** → body size, table text, headings and their weight, where mono appears
- **Density** → control height, row height, sidebar width, the spacing grid
- **Radii and shadows** → per element type; shadows usually only on floating layers
- **Status** → dot plus text, tinted badge, or icon; how each looks in dark
- **Numbers** → alignment, tabular figures, how negatives and money show

Previews are small and compressed, so measurements are estimates. Say so in `look.md`, and round to the grid.

## Citing

- **Every screen used** → a row in `look.md` with the app, what it shows, and its `mobbin_url` as a link
- **Every proposed token** → the screens it was measured from
- **Images** → never commit them; preview links expire after 30 days, and committed folders go unread. The spec's prototype screenshots carry the look from then on
- **Results carry an `ai_usage_notice`** → show it to the requester word for word, as Mobbin requires

## Without the Mobbin connector

- **Ask the requester** for 5 to 10 screenshots or public URLs of apps they like, then read and cite those the same way
- **Neither is available** → stop; a look with no evidence is a guess, and the guess is the same for every app
