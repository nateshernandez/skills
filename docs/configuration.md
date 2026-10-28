# Configuration

kit reads one file, `.claude/kit/config.json`, at the root of your project. `/kit:setup` writes it from a preset and checks it, so you'll rarely write one by hand. This page is the reference for editing it.

Every command runs from the project root through your shell. Unknown fields are an error, so a typo fails loudly instead of being ignored.

## Fields

| Field | Required | What it is |
| --- | --- | --- |
| `check` | yes | The fast gate every task must pass: format check, lint, types, unit tests, build |
| `check_full` | yes | Run once per spec after the last review round: `check` plus visual, accessibility, and other slow suites that aren't the spec's own tests; the gate runs those after it |
| `tests.runner` | yes | `playwright`, `vitest`, or `jest`; picks the test style agents write and how failures are read |
| `tests.acceptance` | yes | Where a spec's end-to-end acceptance tests go; must contain `{spec}` |
| `tests.probes` | yes | Where reviewers' probes go; must contain `{spec}` and `{lens}` |
| `tests.run` | yes | How to run some test files, filtered by title; must contain `{files}` and `{grep}` |
| `tests.unit.runner` | with `tests.unit` | `vitest` or `jest`; the runner for unit-level behavior tests |
| `tests.unit.acceptance` | with `tests.unit` | Where a spec's unit-level behavior tests go; must contain `{spec}`, such as `tests/unit/{spec}.test.ts` |
| `tests.unit.run` | with `tests.unit` | How to run those files, filtered by title; must contain `{files}` and `{grep}` |
| `tests.support` | no | The folder for helpers shared by test files, such as `tests/support`; turns on `check_tests.py` |
| `tests.e2e_per_spec` | no | The most behaviors a spec may test end to end; 4 when left out. Only checked with `tests.unit` |
| `app.serve` | no | Starts the app reviewers share during a round; runs in the background until stopped |
| `app.url` | with `app` | Where the app answers; kit waits for it before reviewers start |
| `app.env` | no | Environment variables for reviewers' test runs, such as `{"REUSE_SERVER": "1"}` |
| `screenshots` | no | Command prefix for screenshots, such as `pnpm exec playwright screenshot`; turns on the UX lens and spec prototypes |
| `audit` | no | Dependency audit the security reviewer runs, such as `pnpm audit --prod` |
| `format.extensions`, `format.run` | no | Formatter run on each file an agent writes; `run` must contain `{file}` |
| `lint.extensions`, `lint.run` | no | Linter run after formatting; its errors go back to the agent in the same turn |
| `design.guide` | with `design` | The design guide agents build UI from and reviewers judge it against, such as `docs/design/guide.md` |
| `design.tokens` | with `design` | The one CSS file that defines colour tokens, such as `src/app/globals.css`; kit checks its contrast |
| `design.gallery` | no | Route of the dev-only gallery that shows every token and component, such as `/design` |
| `design.contrast` | no | Token pairs to check beyond the ones kit finds by name, like `"link on background"` |
| `design.themes` | no | The themes the app ships: `["light", "dark"]` (the default), `["light"]`, or `["dark"]`; checks and screenshots skip the other |
| `architecture.guide` | with `architecture` | The architecture guide agents place code by and reviewers judge it against, such as `docs/architecture/guide.md` |
| `architecture.modules` | with `architecture` | The folder holding one folder per business module, such as `src/modules` |
| `architecture.module_files` | with `architecture` | The only files a module's root may hold, such as `["index.ts", "server.ts", "actions.ts"]` |
| `architecture.module_folders` | with `architecture` | Each folder a module may hold, mapped to the file name globs it allows, such as `{"domain": ["*.ts"]}` |
| `architecture.sources` | with `architecture` | Globs for the source files the line cap applies to, such as `["src/**/*.ts", "src/**/*.tsx"]` |
| `architecture.exempt` | no | Globs `check_shape.py` skips entirely, such as generated or vendored code |
| `architecture.max_lines` | no | The most lines a source file may have; 250 when left out. Test files are exempt |
| `architecture.baseline` | no | Where `check_shape.py --write-baseline` records an existing app's files, such as `.claude/kit/architecture-baseline.json` |
| `build.mode` | no | `standard` (the default) or `turbo`; how `/kit:build` runs a spec that doesn't name its own mode |
| `build.parallel` | no | The most builders at once when a plan has independent tasks; 3 when left out, 1 builds one at a time |
| `build.worktree_setup` | no | Command that makes a fresh git worktree buildable, run from its root with `KIT_MAIN_ROOT` set, such as `pnpm install --frozen-lockfile --prefer-offline` |
| `build.turbo_model` | no | Model for a turbo build's test author, builders, and verifier, such as `sonnet`; unset, they use the session's model |

## Test levels

Every gate runs the tests, so a behavior gets the cheapest test that can fail when it breaks. With `tests.unit` set, the planner gives each behavior a level in plan.md's Tests section and the test author writes it there:

- **Unit and component** → `tests.unit.acceptance`, run by the unit runner; fast enough to run in every task gate
- **End to end** → `tests.acceptance`, run by the browser runner; each test carries a `// e2e: <reason>` line, and a spec has at most `tests.e2e_per_spec` of them

`check_coverage.py` holds to this: one test per behavior across both files, a reason on every end-to-end test, and the budget. A UI-heavy spec that needs more end-to-end tests gets the budget raised in the config by you, not by an agent.

- **Probes are scratch.** The verifier and reviewers delete a probe that passes; the file keeps only the probes that found a defect, so the suite doesn't grow with every review.
- **Helpers are shared.** With `tests.support`, `check_tests.py` runs in every task gate and on each test file an agent writes. It fails a top-level helper of four lines or more declared in two test files, or already in the support folder.
- **Without `tests.unit`** every behavior is tested end to end as before, and neither the reasons nor the budget are checked.

```json
"tests": {
  "runner": "playwright",
  "acceptance": "tests/acceptance/{spec}.spec.ts",
  "probes": "tests/probes/{spec}-{lens}.spec.ts",
  "run": "pnpm exec playwright test {files} --grep {grep}",
  "unit": {
    "runner": "vitest",
    "acceptance": "tests/unit/{spec}.test.ts",
    "run": "pnpm exec vitest run {files} -t {grep}"
  },
  "support": "tests/support",
  "e2e_per_spec": 4
}
```

Put the unit runner in `check` so the task gate runs every unit test, and keep the whole end-to-end suite out of both: the gates run only the spec's own tests, so run the full suite in CI, sharded, to catch a spec breaking an earlier one.

## Design

`/kit:define-design-system` writes the `design` block once its specs are approved. With it set:

- Builders read `design.guide` before building UI, planners name each task's layout and patterns from it, and the UX reviewer judges screens against it
- `check_tokens.py` runs in every task gate and whenever an agent writes a CSS file: it fails when a token pair is below its contrast minimum in a theme from `design.themes`, or when a CSS file other than `design.tokens` holds a raw colour

Pairs kit finds by name, in each theme:

| Tokens | Pair |
| --- | --- |
| `--foreground`, `--background` | foreground on background |
| `--<name>-foreground`, `--<name>` | `<name>-foreground` on `<name>`, like `muted-foreground on muted` |
| `--<name>`, `--<name>-bg` | `<name>` on `<name>-bg`, like `danger on danger-bg` |

Add any other pair to `design.contrast` as `"<token> on <token>"`, without the `--`. The minimum is 4.5:1, the WCAG AA bar for text; follow the pair with a number for another, like `"ring on background 3"` for a focus ring or a control's border.

The light theme is every `:root`, `html`, and `@theme` block. The dark theme is light plus every block whose selector or `@media` query names `dark`, such as `.dark`, `[data-theme="dark"]`, or `prefers-color-scheme: dark`. A colour in another token's `var()` is followed; one kit can't read, like `color-mix()`, is listed as skipped.

An app that ships one theme sets `themes` to it, so kit checks and screenshots only that one. A dark-only app can keep its tokens in `:root`; kit reads them as the dark theme. `check_tokens.py` and `screens.py` take `--theme=light` or `--theme=dark` to do the same before the config has `design`, as a design system's prototypes need.

```json
"design": {
  "guide": "docs/design/guide.md",
  "tokens": "src/app/globals.css",
  "gallery": "/design",
  "contrast": ["link on background", "muted-foreground on surface", "ring on background 3"]
}
```

## Architecture

`/kit:define-architecture` writes the `architecture` block once its spec is approved, with the guide at `docs/architecture/guide.md`. An app whose guide is at `docs/architecture.md` keeps working: `architecture.guide` is the only place the path lives. With it set:

- Planners name each new file's home from `architecture.guide`, builders place code by it, and the code reviewer judges against it
- `check_shape.py` runs in every task gate and on every file an agent writes. It fails when a module's root holds a file outside `module_files`, when a module holds a folder outside `module_folders` or a subfolder in one, when a folder's file matches none of its globs, or when a source file passes `max_lines`

A test file counts as the file it tests, so `ticket-list.test.tsx` is checked as `ticket-list.tsx`. Globs are repo-relative: `**/` spans folders and `*` stays within one; `module_folders` globs match file names only.

An app with code from before the architecture sets `baseline` and runs `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_shape.py --write-baseline`. Files it lists may keep their place, and their length as long as they don't grow; new files meet the shape. Rerun it after moving code, so the list only shrinks.

```json
"architecture": {
  "guide": "docs/architecture/guide.md",
  "modules": "src/modules",
  "module_files": ["index.ts", "server.ts", "actions.ts"],
  "module_folders": {
    "use-cases": ["*.ts"],
    "domain": ["*.ts"],
    "infra": ["*.ts"],
    "components": ["*.tsx", "use-*.ts", "*-state.ts"]
  },
  "sources": ["src/**/*.ts", "src/**/*.tsx"],
  "exempt": ["src/components/ui/**"],
  "max_lines": 250,
  "baseline": ".claude/kit/architecture-baseline.json"
}
```

## Build modes

A standard build plans the spec, runs one builder per task, and reviews it through every lens that applies, for up to three rounds. A turbo build is faster: one builder builds the whole spec, and one review round checks it.

| Step | Standard | Turbo |
| --- | --- | --- |
| Spec, prototype, and your approval | ✓ | ✓ |
| Planner: plan, threat model, decisions to record | ✓ | ✗ one task covering every behavior |
| Failing acceptance tests, written before code | ✓ | ✓ |
| Builders | one per task, side by side when tasks are independent | one for the spec |
| Task gate and stop gate, including the design and shape checks | ✓ | ✓ |
| Verifier | ✓ | ✓ |
| Security reviewer, when input, storage, auth, or secrets change | ✓ | ✓ |
| Code reviewer | ✓ | ✗ |
| UX reviewer, when UI changes and `screenshots` is set | ✓ | ✗ |
| Review rounds | up to 3 | 1; its fixes pass the gate but aren't reviewed again |
| Full gate | ✓ | ✓ |
| Decision records, rules, and guide updates | ✓ | ✗ |

Pick the mode per build with `/kit:build --turbo <request>` or `--standard`, or set a default:

```json
"build": { "mode": "turbo", "turbo_model": "sonnet" }
```

The mode is written into the spec's frontmatter as `mode:`, so you see it when you approve and a resumed build keeps it. A turbo report lists what it skipped under Skipped. To run the skipped reviews before merging, resume with `/kit:build <id> --standard`; it reviews the build as round 2.

`turbo_model` applies only to turbo builds, and never to the security reviewer. It takes whatever the Agent tool accepts: an alias such as `sonnet` or `haiku`, or a full model ID.

## Parallel builds

A standard build whose plan lists `needs` and `files` on each task builds independent tasks side by side. Each builder works in its own git worktree on its own branch, with its own gate and port, and the orchestrator lands finished tasks onto the spec's branch one by one, so history stays linear.

- **`build.worktree_setup`** is what a fresh worktree needs before it can build: dependencies, and local files that aren't in git. `KIT_MAIN_ROOT` is the main checkout, so a setup can copy from it:

  ```json
  "build": {
    "parallel": 3,
    "worktree_setup": "pnpm install --frozen-lockfile --prefer-offline && cp \"$KIT_MAIN_ROOT/.env.local\" .env.local"
  }
  ```

- **`check_tasks.py`** fails a plan in which two tasks that may run together write the same path
- **`mark_task.py`** fails a task that changed a file it didn't list, before its gate runs
- **Gates and ports** are per worktree, so concurrent gates don't wait on each other or share a server
- **Landing** is `land_task.py`: it checks the task passed in its worktree and stayed within its `files`, replays its commits on the spec's branch, and removes the worktree. After each wave one gate runs on the merged tree
- **A task list with no `needs` or `files`** is sequential, and a turbo or size S build always uses one builder

Set `build.parallel` to 1 to turn waves off.

## Deck style

Decks read their own file, not `config.json`: `docs/deck/style.json`, or a deck's own `decks/<id>/style.json`, which replaces it for that deck. `/kit:define-deck-style` writes it; [skills/define-deck-style/references/style-format.md](../skills/define-deck-style/references/style-format.md) is the full reference. Unknown fields are an error.

| Field | Required | What it is |
| --- | --- | --- |
| `kind` | no | `presented` (the default) or `read`; a read deck's slides may hold 2.5 times the words |
| `fonts` | yes | `heading` and `body`, and any other role, each `{family, href}`; `href` is a `https://fonts.googleapis.com/css2?…` link, left out for a basic face; at most 3 families |
| `colors` | yes | Named `#rrggbb` colours including `background`, `text`, `muted`, `accent`; every opaque colour on a slide must be one |
| `sizes` | yes | Named px sizes including `title`, `body`, `small`; at most 5, none under 24; every text element must use one |
| `titles.case` | no | `sentence` (the default), `title`, or `any` |
| `titles.max_words` | no | The most words a slide title may have, 4 to 25; 15 when left out |
| `banned` | no | Phrases that fail the lint, added to kit's own list |

`render_deck.py` needs Chrome or Chromium. It looks in the usual install paths and Playwright's download; set `KIT_BROWSER` to a browser binary to use another.

## Placeholders

kit fills these in and shell-quotes each value, so don't add quotes around them.

| Placeholder | In | Becomes |
| --- | --- | --- |
| `{spec}` | `tests.acceptance`, `tests.probes` | The spec ID, like `001-waitlist` |
| `{lens}` | `tests.probes` | `quality`, `ux`, `security`, or `code` |
| `{files}` | `tests.run`, `tests.unit.run` | The spec's test files for that runner: end to end plus probes, or unit level |
| `{grep}` | `tests.run` | A title regex that leaves out behaviors still being built, or `^` to run everything |
| `{file}` | `format.run`, `lint.run` | The absolute path of the file just written |

`{grep}` relies on test titles starting with the behavior ID, like `test("1.B2 Visitor joins with \"abc\"")`. Pass it to the runner's title filter:

| Runner | `tests.run` |
| --- | --- |
| Playwright | `pnpm exec playwright test {files} --grep {grep}` |
| Vitest | `pnpm exec vitest run {files} -t {grep}` |
| Jest | `npx jest {files} -t {grep}` |

## Environment variables kit sets

| Variable | When | Use it for |
| --- | --- | --- |
| `KIT_PORT` | Every gate run and reviewer test run | A free port, with the next three also free. Point your test server at it, so a gate never reuses a stale server |
| `KIT_APP_URL` | Reviewer test runs, when `app` is set | The shared review app's URL |
| `NO_COLOR` | Every gate run | Keeps color codes out of the failing-test titles kit reports |

For Playwright, read both in `playwright.config.ts`:

```ts
const port = Number(process.env.KIT_PORT ?? 3000);

export default defineConfig({
  use: { baseURL: process.env.KIT_APP_URL ?? `http://localhost:${port}` },
  webServer: {
    command: `pnpm build && pnpm start --port ${port}`,
    port,
    reuseExistingServer: process.env.REUSE_SERVER === "1",
  },
});
```

## Examples

A Next.js app tested with Playwright:

```json
{
  "check": "pnpm lint && pnpm typecheck && pnpm test && pnpm build",
  "check_full": "pnpm lint && pnpm typecheck && pnpm test && pnpm build",
  "tests": {
    "runner": "playwright",
    "acceptance": "tests/acceptance/{spec}.spec.ts",
    "probes": "tests/probes/{spec}-{lens}.spec.ts",
    "run": "pnpm exec playwright test {files} --grep {grep}"
  },
  "app": {
    "serve": "pnpm build && pnpm start --port 3100",
    "url": "http://localhost:3100",
    "env": { "REUSE_SERVER": "1" }
  },
  "screenshots": "pnpm exec playwright screenshot --load-storage=tests/.auth/state.json",
  "audit": "pnpm audit --prod",
  "format": {
    "extensions": [".ts", ".tsx", ".css"],
    "run": "node_modules/.bin/prettier --write --log-level silent {file}"
  },
  "lint": {
    "extensions": [".ts", ".tsx"],
    "run": "node_modules/.bin/eslint --no-warn-ignored {file}"
  }
}
```

A library tested with Vitest, formatted and linted by Biome:

```json
{
  "check": "pnpm biome ci . && pnpm tsc --noEmit && pnpm vitest run",
  "check_full": "pnpm biome ci . && pnpm tsc --noEmit && pnpm vitest run && pnpm build",
  "tests": {
    "runner": "vitest",
    "acceptance": "tests/acceptance/{spec}.test.ts",
    "probes": "tests/probes/{spec}-{lens}.test.ts",
    "run": "pnpm exec vitest run {files} -t {grep}"
  },
  "format": {
    "extensions": [".ts"],
    "run": "node_modules/.bin/biome check --write {file}"
  }
}
```

## Project checklists

Reviewers start from kit's generic checklists. Add your stack's checks in `.claude/kit/checklists/<lens>.md`, where lens is `code`, `security`, or `ux`. Plain bullets work:

```markdown
# Code checklist: this project

- Server components by default; `"use client"` only at the leaves that need state
- Every query goes through `src/db/scoped.ts`, never the raw client
```

## Checking the config

Run `/kit:setup` again after editing the config. It runs kit's readiness checks (Python, git, the config, each command it names, and a green `check`), then fixes only what they flag.
