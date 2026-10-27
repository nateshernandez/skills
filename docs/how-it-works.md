# How kit works

kit is a Claude Code plugin made of skills (what to do), agents (who does it, with which tools and files), scripts (checks that don't drift), and hooks (which run those checks without being asked). This page explains the pieces you'll see while a build runs.

## A product starts with a brief

`/kit:define-product` runs before anything is built and writes `docs/product/`. It works like a build, aimed at the business instead of the code:

- **Evidence before opinion.** The market researcher writes `market.md` from the idea alone, so research isn't bent to fit a draft. Each source is a link, and Reddit counts come from `reddit_search.py` with a URL that reruns the search.
- **Graded claims.** Every claim in `brief.md` is `sourced` or `inferred` (citing `market.md`'s M IDs), `assumed` or `validated` (citing a `PA` assumption), or `stated` by you. `lint_product.py` checks that each citation exists, and that `validated` points at an assumption that `holds`.
- **An independent skeptic.** The product reviewer reads the files from fresh context and writes blocker or note findings, each with evidence, just like a build's reviewers.
- **A verdict with rules.** `go` can't stand with any dimension rated `weak`, and `go` or `narrow` needs a first version in which every feature tests an assumption.
- **Permanent IDs.** Once the brief is approved, its `PD`, `PA`, and `PF` IDs keep their wording; changing one means retiring it, as in a spec.

## Docs have one front door per area

Each area under `docs/` has one file agents read by default and a `research/` folder for the evidence behind it, read only when a claim needs checking:

- `docs/product/brief.md` is the whole product on one page; its claims cite `research/market.md` by ID, so a separate summary would only drift
- `docs/design/guide.md` is the design system; `research/look.md` holds the measured screens it came from
- `docs/architecture/guide.md` says where code goes, beside one file per system design (a data model, a protocol) promoted from a spec's `design.md` after review
- `docs/decisions/` holds one record per choice

A project that already has `docs/product/market.md` or `docs/product/reviews/` keeps working: kit looks in both places. New runs write under `research/`.

## A deck is built like a feature

`/kit:write-deck` makes presentations with the same pieces, aimed at an argument instead of code. It needs no kit config, so it works in any folder.

- **The storyline is the contract.** `decks/<id>/storyline.md` has the audience, the ask, and one item per slide: an `S` number, an id, a layout, and the title as a full-sentence claim, with what evidence the slide shows. `render_deck.py --wireframes` draws each slide with its real title, so you approve the argument and its shape together.
- **Titles carry the story.** Each slide's heading must match its storyline title word for word, so the deck you approved is the deck that ships. A content title is a claim of 4 to 15 words, never a question, a list of three, or a phrase from the copy list.
- **Two checks, like a gate.** `lint_deck.py` reads the files: word caps per layout, list lengths, colours and sizes from the style only, speaker notes on every presented slide, and the tells of generated copy. `render_deck.py` renders each slide in headless Chrome at 1920×1080 and fails overflow, text outside the margins, overlapping text, low contrast, a title past two lines, a heading that moves between content slides, and a body that floats away from its heading.
- **Three lenses.** The story, design, and copy reviewers each start from fresh context. The copy reviewer reads only the slides, never the storyline, so it meets the words the way the audience will.
- **The repo is the source; Slides is the stage.** `publish_deck.py` stages the files a Claude Slides artifact expects and sends only the slides that changed. Before applying comments it pulls your hand edits back into the repo, so nothing you changed in Slides is overwritten.
- **A house style.** `docs/deck/style.json` sets fonts, colours, sizes, title rules, and banned phrases, and the scripts enforce them. `guide.md` holds house rules that need judgment, and `voice.md` quotes your own writing so slides and notes sound like you.

## The spec is the contract

A spec is one screen of bullets in `specs/<NNN>-<slug>/spec.md`:

- **Outcome**: one line saying what's true for the user when it ships
- **Decide**: choices the request left open, each with the default kit picked and its strongest alternative (`3.D1`)
- **Behaviors**: what you'll observe, each with an outcome a test can check (`3.B1`)
- **Not doing**: the scope fence

IDs are permanent once you approve. Tests, tasks, findings, and the report all cite them, so changing an approved item means retiring its ID and adding a new one. `lint_spec.py` compares each edit against the last approved version to enforce this, and `check_ids.py` flags anything that still cites a retired ID.

Limits keep specs reviewable: 50 lines, 5 decisions, 12 behaviors. A bigger feature becomes two specs.

## A complex feature gets a design

When a spec fixes a shape that is costly to change, such as a data model with versioning or a protocol between agents, the designer writes `specs/<id>/design.md` after you approve the spec and before the plan. It holds types, interfaces, mermaid flows, and numbered invariants (`5.I2 Version numbers → count up by one per document with no gaps`), in 80 lines or fewer. You approve it, because it's the part you can't cheaply change later.

- Each invariant gets a unit test, and `check_coverage.py` fails one without
- The planner cuts tasks along the design's interfaces, so tasks can be built side by side
- The code reviewer blocks a diff that drifts from the interfaces or breaks an invariant
- After review, the shapes later specs build on move to `docs/architecture/<topic>.md`

## Gates decide when a task is done

The builder never marks its own task done. `mark_task.py` runs the **task gate** and flips `passes` only when it's green:

1. Your `check` command
2. `check_tokens.py`, when the config has `design`: token contrast in each theme the app ships, and no colour outside the tokens file
3. `check_shape.py`, when the config has `architecture`: each module's files in their places, and no source file past the line cap
4. `check_tests.py`, when the config has `tests.support`: no helper copied between test files
5. The spec's behavior tests (unit level first, then end to end) and probes, minus behaviors that later tasks will build, and minus the whole-feature `outcome` probes

The **full gate** runs once per spec, after the last review round: `check_full`, the same checks, then every delivered behavior's tests and the outcome probes.

Both gates log to a temp file and print only the failing test titles and the log's tail. A green run stamps the working tree, so rerunning on an unchanged tree returns at once. When a builder tries to stop with a red gate, the stop hook sends it back, at most three times in a row.

## Each behavior is tested at the cheapest level

The planner gives every behavior a level in plan.md: unit, component, or end to end. Rules (what's allowed, how much, what text results) are unit tests, which run in every task gate in seconds. A behavior that needs a real browser, a journey where a miss costs most, or the layers wired together is end to end, with a `// e2e: <reason>` above its test. A spec may have only `tests.e2e_per_spec` of those, so the slow suite grows by decision, not by default.

Test files share helpers through `tests.support`. `check_tests.py` fails a helper copied into two files, and the test author, verifier, and builder read the support folder before writing their own.

## Agents can only write their own files

Each agent's frontmatter lists the files it may write (`fence-allow`) or may not (`fence-deny`). The `fence.py` hook enforces those lists before any write or obvious shell write.

| Agent | Writes | Reads |
| --- | --- | --- |
| market-researcher | `docs/product/research/market.md` | the idea, the web, Reddit through Arctic Shift |
| product-reviewer | product review findings | brief, market research, the web |
| designer | `design.md` | spec, code, architecture docs, decisions |
| planner | `plan.md`, `tasks.json` | spec, design, code, decisions |
| test-author | behavior tests (end to end and unit level), shared test helpers | spec, plan's tests and routes |
| builder | app code, colocated unit tests, shared test helpers; not specs, tasks, behavior tests, probes, reviews, or `.claude/` | spec, plan, progress, tests |
| verifier | quality probes, quality findings, screens | the spec only |
| code-reviewer | code findings | the diff, rules, decisions |
| security-reviewer | security probes, security findings | the diff, plan's risks |
| ux-reviewer | UX probes, UX findings, screens | spec, screenshots |
| slide-builder | a deck's slides, assets, screens | storyline, style, guide, voice, sources |
| deck-reviewer | deck review findings | its lens's inputs only |

Fences apply once `.claude/kit/config.json` exists, so a product brief written before setup runs unfenced. Fences work for your own agents too: add `fence-allow` or `fence-deny` to an agent in `.claude/agents/`.

## Reviews need evidence

Each reviewer writes `specs/<id>/reviews/<lens>-r<round>.md`. Every finding is a `blocker` or a `note`, and each one carries exactly one piece of evidence: a failing probe, a screenshot, command output, or a `file:line`. Blockers become fix tasks (`F1`, `F2`, ...) for the next round. After three rounds with blockers left, the spec is marked `blocked`, and the report asks you one question per blocker.

A probe is a question, not a test to keep: one that passes is deleted. A probe that fails stays, because the fix task and every later gate need it, so the suite grows only with defects found.

## Turbo builds trade review for speed

A turbo build skips the planner, runs one builder for the whole spec, and reviews once with the verifier, plus the security reviewer when input, storage, auth, or secrets change. Blockers become one fix task that must pass the gate, with no second round, and nothing is codified. The spec, its prototype, your approval, the acceptance tests, the gates, and the full gate are the same as in a standard build. The report's Skipped section names each step left out. [configuration.md](configuration.md#build-modes) compares the two modes step by step.

## Builds leave context behind

After the last round passes, the orchestrator codifies what the build settled:

- **Decision records** in `docs/decisions/` for each choice in the plan marked `record`, written against the reviewed code, with `code:` paths a reader opens first
- **Rules** in `.claude/rules/` for patterns later code must repeat, scoped by `paths:` so they load only where they apply
- **Design guide sections** in `docs/design/guide.md` for a UI piece a second feature reused, moved into the shared components
- **Architecture guide lines** in `docs/architecture/guide.md` for code a second module needed, moved down to its shared home

Each is listed under Codified in the report, for you to confirm before merging.

## Commits

Setup adds `.claude/rules/git-commits.md`, an always-on rule every session follows, unless your project already has commit conventions:

- Subjects are imperative, 50 characters or fewer, with no type prefix; bodies only for a why the diff can't show
- One commit per change, with files staged by name
- Work happens on a branch, never directly on `main`, and the branch is rebased onto `main`, never merged
- Pushing, amending, rebasing a pushed branch, and force-pushing wait for your yes

A build commits the spec, the acceptance tests, each task, each review round's findings, and the codified records, so `git log --oneline` reads as the build's story.

## Hooks

| Hook | Script | What it does |
| --- | --- | --- |
| Before a write | `fence.py` | Blocks a subagent's write outside its fence |
| After a write | `on_write.py` | Formats and lints source files; lints specs, designs, findings, reports, probes, product files, deck files, decisions, skills, rules, agents, and the `.claude/` changelog; checks CSS files' colours when the config has `design`, and each file's place and length when it has `architecture` |
| When a subagent stops | `gate.py --hook` | Sends kit's builder back to work while the task gate is red |
| When a subagent stops | `lint_product.py --hook` | Sends the market researcher or product reviewer back while its file fails the lint |

All four exit at once in a project without `.claude/kit/config.json`.

## Writing your own skills, rules, and agents

kit's skills follow one format: a routing description (`Use when:` and `Not when:`), then Goal, In, Out, a Flow diagram, Rules with reasons, Done When, and Never, in 60 lines or fewer. `/kit:write-skill`, `/kit:write-rule`, and `/kit:write-agent` write your project's own in the same shape, and the write hook lints them.
