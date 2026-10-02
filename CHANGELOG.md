# Changelog

What each release of kit changes for the people using it. Newest first.

## 0.2.0 (2026-10-02)

- **Added** `/kit:design-system`: researches a look on Mobbin, then writes `docs/design/look.md`, a design foundations spec, a core screens spec, and the design guide agents build UI from; a recipe for Next.js, Tailwind 4, and shadcn
- **Added** `check_tokens.py`: fails a token pair under WCAG AA contrast in light or dark, or a colour in any CSS file but the tokens file; runs in every gate and on each CSS write when the config has `design`
- **Added** a `design` config block naming the guide, the tokens file, the gallery, and extra contrast pairs
- **Added** `tests/kit/ux-checks.ts`, copied by setup into Playwright apps: side scroll, tap targets, clipped text, lost focus, and axe
- **Changed** the UX review's blocker bar: focus lost to the page, missing waiting, success, or failure states, dead ends, unreadable text at 390px, tap targets under 44px, failed contrast, and breaking the design guide now block
- **Changed** specs with UI cover each screen's empty, loading, error, phone, and longest-content states; a screen the guide lacks gets a decision backed by Mobbin research
- **Changed** planners name each screen's layout and patterns from the guide, builders follow it, and a UI piece a second feature reuses moves into it

## 0.1.0 (2026-10-02)

- **Added** the build pipeline: `/kit:build` takes a request through spec, plan, failing tests, task-by-task build, four-lens review, and a report
- **Added** `/kit:setup`: detects the stack, writes `.claude/kit/config.json` from a Playwright, Vitest, or Jest preset, and checks the gate is green
- **Added** gates: `mark_task.py` marks a task done only when `check` and the spec's tests pass, skipping behaviors later tasks will build
- **Added** hooks: write fences per agent, format and lint on every write, and a stop gate that keeps a builder working while its gate is red
- **Added** authoring skills for decision records, rules, skills, agents, and a `.claude/` changelog, each with its own lint
- **Added** a commit rule that setup installs: short imperative subjects, one commit per change, branches rebased onto `main`
