# UX and design checklist

kit's bar for every app. The project's design guide (`design.guide` in the config) sets its look, layouts, and patterns; its own checklist, `.claude/kit/checklists/ux.md`, can raise the bar below.

## Blocker bar

- **Main task can't be finished** at 390px or 1280px
- **Keyboard alone can't finish it**, or focus is invisible
- **Focus falls to the page body** after an action, or after an overlay or the focused control closes
- **A state is missing**: an action shows nothing while it waits, when it succeeds, or when it fails
- **Error doesn't say how to recover**
- **Dead end**: a page or state with no way back or on, a missing page included
- **Text is cut off, overlaps, or scrolls sideways**; text a person or the data wrote, like a name or an email, can't be read in full at 390px
- **Tap target under 44px** at 390px, links inside running text aside
- **Contrast fails** WCAG AA in light or dark, as axe reports it
- **Looks foreign**: hand-rolls a control the project's components already have, or ignores its tokens
- **Breaks the design guide**: the guide has a rule for this case and the screen doesn't follow it; cite the guide's line

## Notes (not blockers)

- Spacing, alignment, hierarchy that could be clearer
- Copy that could be shorter or plainer, or names one thing two ways ("Sign in" and "Log in")
- Empty states that could guide better
- A case the design guide doesn't cover yet; name the rule it needs

## How to look

- **Run the UX checks** → in the UX probe, `uxProblems(page)` from `tests/kit/ux-checks.ts` on each route at 390px, light and dark; `focusLost(page)` after each action
  - Missing the file → kit's setup copies it; check the same things by hand and say so in a note
- **Fill the worst case** → the longest name and email, many items, zero items, a slow response
- **Act, then look** → after every action, where is focus, and what says it worked or failed?
- **Squint test** → is the most important thing the most visible?
- **Read every word** on screen as a first-time visitor
- **Compare** against the design guide's layout for this screen, then an existing screen of the app, for type scale, spacing, and colour
- **Check both themes**; a colour that works in one often fails in the other
