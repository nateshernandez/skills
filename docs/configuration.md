# Configuration

kit reads one file, `.claude/kit/config.json`, at the root of your project. `/kit:setup` writes it from a preset and checks it, so you'll rarely write one by hand. This page is the reference for editing it.

Every command runs from the project root through your shell. Unknown fields are an error, so a typo fails loudly instead of being ignored.

## Fields

| Field | Required | What it is |
| --- | --- | --- |
| `check` | yes | The fast gate every task must pass: format check, lint, types, unit tests, build |
| `check_full` | yes | Everything, run once per spec after the last review round: `check` plus e2e, visual, and other slow suites |
| `tests.runner` | yes | `playwright`, `vitest`, or `jest`; picks the test style agents write and how failures are read |
| `tests.acceptance` | yes | Where a spec's acceptance tests go; must contain `{spec}` |
| `tests.probes` | yes | Where reviewers' probes go; must contain `{spec}` and `{lens}` |
| `tests.run` | yes | How to run some test files, filtered by title; must contain `{files}` and `{grep}` |
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

## Design

`/kit:design-system` writes the `design` block once its specs are approved. With it set:

- Builders read `design.guide` before building UI, planners name each task's layout and patterns from it, and the UX reviewer judges screens against it
- `check_tokens.py` runs in every task gate and whenever an agent writes a CSS file: it fails when a token pair is below its contrast minimum in light or dark, or when a CSS file other than `design.tokens` holds a raw colour

Pairs kit finds by name, in both themes:

| Tokens | Pair |
| --- | --- |
| `--foreground`, `--background` | foreground on background |
| `--<name>-foreground`, `--<name>` | `<name>-foreground` on `<name>`, like `muted-foreground on muted` |
| `--<name>`, `--<name>-bg` | `<name>` on `<name>-bg`, like `danger on danger-bg` |

Add any other pair to `design.contrast` as `"<token> on <token>"`, without the `--`. The minimum is 4.5:1, the WCAG AA bar for text; follow the pair with a number for another, like `"ring on background 3"` for a focus ring or a control's border.

The light theme is every `:root`, `html`, and `@theme` block. The dark theme is light plus every block whose selector or `@media` query names `dark`, such as `.dark`, `[data-theme="dark"]`, or `prefers-color-scheme: dark`. A colour in another token's `var()` is followed; one kit can't read, like `color-mix()`, is listed as skipped.

```json
"design": {
  "guide": "docs/design/guide.md",
  "tokens": "src/app/globals.css",
  "gallery": "/design",
  "contrast": ["link on background", "muted-foreground on surface", "ring on background 3"]
}
```

## Placeholders

kit fills these in and shell-quotes each value, so don't add quotes around them.

| Placeholder | In | Becomes |
| --- | --- | --- |
| `{spec}` | `tests.acceptance`, `tests.probes` | The spec ID, like `001-waitlist` |
| `{lens}` | `tests.probes` | `quality`, `ux`, `security`, or `code` |
| `{files}` | `tests.run` | The spec's acceptance test file and probe files |
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
  "check_full": "pnpm lint && pnpm typecheck && pnpm test && pnpm build && pnpm exec playwright test",
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
