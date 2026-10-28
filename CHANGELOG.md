# Changelog

What each release of kit changes for the people using it. Newest first.

## 0.8.0 (2026-10-27)

- **Changed** the Playwright preset's `check_full`: it no longer runs the whole e2e suite, since the full gate already runs the spec's own tests; run every spec's tests in CI, and drop `playwright test` from `check_full` in an existing config to match
- **Changed** the gate: test steps get `KIT_BUILT=1` once `check` passes, so a Playwright `webServer` can skip its second `pnpm build`; read it in `playwright.config.ts` if your `check` builds

## 0.7.0 (2026-10-27)

- **Changed** `/kit:build`: before the full gate, the probes that found a defect become unit tests beside their code and the probe files are deleted, so you no longer have to ask for it; a probe only a real browser can prove stays and is listed in the report

## 0.6.0 (2026-10-27)

- **Added** `tests.unit`, `tests.support`, and `tests.e2e_per_spec` in the config: the planner gives each behavior a unit, component, or end-to-end level, unit-level tests run in every task gate, and `check_coverage.py` fails an end-to-end test with no `// e2e:` reason or a spec past its budget of 4
- **Added** `check_tests.py`: fails a test helper copied between test files, in every task gate and on each test file an agent writes, when the config has `tests.support`
- **Added** `design.md` and the `designer` agent: when a spec fixes a data model, protocol, state machine, or contract, you approve a short design with types, flows, and numbered invariants before the plan, and each invariant gets a unit test
- **Added** parallel builds: a plan's tasks list `needs` and `files`, and independent tasks build side by side in separate git worktrees that `land_task.py` replays onto the spec's branch; `build.parallel` and `build.worktree_setup` in the config tune it
- **Added** `ready now` in `spec_status.py`, and a check in `mark_task.py` that fails a task which changed a file it didn't list
- **Changed** probes: the verifier and the UX and security reviewers delete a probe that passes, so the suite keeps only probes that found a defect
- **Changed** new product research lands in `docs/product/research/`, the architecture guide in `docs/architecture/guide.md`, and the design research in `docs/design/research/look.md`; files at the old paths still work, and `architecture.guide` keeps whatever path you set
- **Changed** `/kit:setup` presets: Playwright projects get a Vitest unit level and `tests/support`, and every preset gets a `build.worktree_setup` install command to check

## 0.5.0 (2026-10-05)

- **Added** `/kit:write-deck`: writes a presentation as a storyline you approve with wireframes, builds the slides, reviews them for story, design, and copy, and publishes them to a Claude Slides deck you can present, comment on, and export
- **Added** `/kit:define-deck-style`: turns brand files in `docs/deck/brand/` into a deck style, house rules, and a voice guide, shown as a specimen deck
- **Added** `lint_deck.py` and `render_deck.py`: fail a deck's slides on title rules, word caps, off-style colours and sizes, generated-sounding copy, overflow, overlap, low contrast, and headings that move; deck files are linted on each write
- **Added** `/kit:define-product`: researches an idea's market, including Reddit counts through Arctic Shift, writes a product brief with graded evidence, has a skeptical reviewer challenge it, and ends with a verdict and a validation plan
- **Added** `lint_product.py`: checks the brief's citations and verdict rules on each write and before the market researcher or product reviewer stops
- **Changed** `/kit:architecture` is now `/kit:define-architecture` and `/kit:design-system` is now `/kit:define-design-system`; call them by the new names
- **Changed** specs, setup, the design system, and the architecture read `docs/product/brief.md` when it exists

## 0.4.0 (2026-10-02)

- **Added** `design.themes` in the config: an app that ships only light or only dark sets it, and contrast checks, screenshots, and UX reviews cover just that theme
- **Added** `--theme=light` or `--theme=dark` on `check_tokens.py` and `screens.py`, for a one-theme app's prototypes before the config has `design`
- **Changed** `/kit:design-system` asks whether the app ships light, dark, or both, and a one-theme app gets no theme switcher, no `.dark` tokens, and specs in that theme only

## 0.3.0 (2026-10-02)

- **Added** `/kit:architecture`: writes an architecture spec and `docs/architecture.md` that give every file one home by layer and module, plus the recipe's rules; a recipe for Next.js, and a baseline so an app with existing code can adopt it
- **Added** `check_shape.py`: fails a file outside its module's allowed places, or a source file past the line cap; runs in every gate and on each write when the config has `architecture`
- **Added** an `architecture` config block naming the guide, the modules folder, each module's allowed files and folders, the sources, exemptions, line cap, and baseline
- **Added** turbo builds: `/kit:build --turbo` runs one builder and one review round with the verifier, plus the security reviewer when triggered; the report lists what it skipped, and `--standard` runs those reviews later
- **Added** a `build` config block: `mode` makes turbo the default, and `turbo_model` runs turbo's test author, builders, and verifier on a faster model
- **Changed** planners name each new file's home from the architecture guide, builders place code by it, and the code review blocks a file outside the home the guide gives it
- **Changed** `/kit:setup` suggests `/kit:architecture` once the gate is green

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
