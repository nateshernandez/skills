# How kit works

kit is a Claude Code plugin made of skills (what to do), agents (who does it, with which tools and files), scripts (checks that don't drift), and hooks (which run those checks without being asked). This page explains the pieces you'll see while a build runs.

## The spec is the contract

A spec is one screen of bullets in `specs/<NNN>-<slug>/spec.md`:

- **Outcome**: one line saying what's true for the user when it ships
- **Decide**: choices the request left open, each with the default kit picked and its strongest alternative (`3.D1`)
- **Behaviors**: what you'll observe, each with an outcome a test can check (`3.B1`)
- **Not doing**: the scope fence

IDs are permanent once you approve. Tests, tasks, findings, and the report all cite them, so changing an approved item means retiring its ID and adding a new one. `lint_spec.py` compares each edit against the last approved version to enforce this, and `check_ids.py` flags anything that still cites a retired ID.

Limits keep specs reviewable: 50 lines, 5 decisions, 12 behaviors. A bigger feature becomes two specs.

## Gates decide when a task is done

The builder never marks its own task done. `mark_task.py` runs the **task gate** and flips `passes` only when it's green:

1. Your `check` command
2. `check_tokens.py`, when the config has `design`: token contrast in light and dark, and no colour outside the tokens file
3. `check_shape.py`, when the config has `architecture`: each module's files in their places, and no source file past the line cap
4. The spec's acceptance tests and probes, minus behaviors that later tasks will build, and minus the whole-feature `outcome` probes

The **full gate** runs once per spec, after the last review round: `check_full`, `check_tokens.py`, `check_shape.py`, then every delivered behavior's tests and the outcome probes.

Both gates log to a temp file and print only the failing test titles and the log's tail. A green run stamps the working tree, so rerunning on an unchanged tree returns at once. When a builder tries to stop with a red gate, the stop hook sends it back, at most three times in a row.

## Agents can only write their own files

Each agent's frontmatter lists the files it may write (`fence-allow`) or may not (`fence-deny`). The `fence.py` hook enforces those lists before any write or obvious shell write.

| Agent | Writes | Reads |
| --- | --- | --- |
| planner | `plan.md`, `tasks.json` | spec, code, decisions |
| test-author | acceptance tests | spec, plan's routes |
| builder | app code and unit tests; not specs, tasks, tests, probes, reviews, or `.claude/` | spec, plan, progress, tests |
| verifier | quality probes, quality findings, screens | the spec only |
| code-reviewer | code findings | the diff, rules, decisions |
| security-reviewer | security probes, security findings | the diff, plan's risks |
| ux-reviewer | UX probes, UX findings, screens | spec, screenshots |

Fences work for your own agents too: add `fence-allow` or `fence-deny` to an agent in `.claude/agents/`.

## Reviews need evidence

Each reviewer writes `specs/<id>/reviews/<lens>-r<round>.md`. Every finding is a `blocker` or a `note`, and each one carries exactly one piece of evidence: a failing probe, a screenshot, command output, or a `file:line`. Blockers become fix tasks (`F1`, `F2`, ...) for the next round. After three rounds with blockers left, the spec is marked `blocked`, and the report asks you one question per blocker.

Probes that pass are kept, so every later gate also runs them as regression tests.

## Builds leave context behind

After the last round passes, the orchestrator codifies what the build settled:

- **Decision records** in `docs/decisions/` for each choice in the plan marked `record`, written against the reviewed code, with `code:` paths a reader opens first
- **Rules** in `.claude/rules/` for patterns later code must repeat, scoped by `paths:` so they load only where they apply
- **Design guide sections** in `docs/design/guide.md` for a UI piece a second feature reused, moved into the shared components
- **Architecture guide lines** in `docs/architecture.md` for code a second module needed, moved down to its shared home

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
| After a write | `on_write.py` | Formats and lints source files; lints specs, findings, reports, probes, decisions, skills, rules, agents, and the `.claude/` changelog; checks CSS files' colours when the config has `design`, and each file's place and length when it has `architecture` |
| When a subagent stops | `gate.py --hook` | Sends kit's builder back to work while the task gate is red |

All three exit at once in a project without `.claude/kit/config.json`.

## Writing your own skills, rules, and agents

kit's skills follow one format: a routing description (`Use when:` and `Not when:`), then Goal, In, Out, a Flow diagram, Rules with reasons, Done When, and Never, in 60 lines or fewer. `/kit:write-skill`, `/kit:write-rule`, and `/kit:write-agent` write your project's own in the same shape, and the write hook lints them.
