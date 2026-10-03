# Validation

Research shows who's building what and what people complain about. Only customers' behavior shows whether they'll pay. `docs/product/validation.md` turns each untested PA into the cheapest test that could fail it, and records what happened.

## Choosing a test

- **One assumption per test** → name the PA it settles
- **Decide the bar first** → write the result that counts as `holds` before running it, so a weak result can't be argued into a pass
- **Cheapest first** → interviews, then a smoke test, then a concierge test, then building
- **Order** → the riskiest PA first: the one that, if false, makes everything else moot

## Interviews

Five to ten people from the beachhead, found where market.md found them. The rules come from Rob Fitzpatrick's *The Mom Test*: people lie about the future to be kind, but not about the past.

- **Ask about the past** → "Walk me through last month-end" ✓ "Would you use an app that…" ✗
- **Ask for specifics** → how many hours, which tools, what it cost, who decided
- **Ask what they've tried** → anyone who has never looked for a fix doesn't feel the pain much
- **Ask about money** → "What do you pay for that today?" beats "Would you pay $29?"
- **Don't pitch** → describe the product only at the end, if at all; then ask for a commitment
- **A commitment** → time (a second call), reputation (an intro), or money (a pre-order); compliments count for nothing
- **Finding people** → follow each community's rules; a short honest post asking for 20 minutes works better than cold DMs

## Smoke tests

- **Landing page with the price** → a page that pitches the product at its real price, with a sign-up; `/kit:build` can build it
  - Measures willingness to pay better than any survey; the bar is sign-ups per visitor from one named channel
- **Fake door** → a button for the feature in an existing product; count clicks
- **Concierge** → deliver the result by hand for a few customers; learn the job before automating it
- **Pre-sale** → ask for payment before building; the strongest signal there is

## Recording results

- **Each result** → the date, the PA, what was run, the numbers, and `holds` or `fails` against the bar set beforehand
- **Then** → update the PA's status in the brief and re-run `/kit:define-product` so the review and verdict see it
- **Notes** → keep raw interview notes out of the repo or strip names; record only what the brief needs
