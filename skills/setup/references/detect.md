# Detecting the stack

Fill each config value from the project's files. Ask the requester only when two answers are equally likely. `docs/configuration.md` in the kit repo documents every field.

## Package manager

- **`pnpm-lock.yaml`** → `pnpm <script>`, `pnpm exec <bin>`
- **`yarn.lock`** → `yarn <script>`, `yarn <bin>`
- **`bun.lock` or `bun.lockb`** → `bun run <script>`, `bunx <bin>`
- **`package-lock.json`, or none** → `npm run <script>`, `npx <bin>`
- Replace `pnpm` in a preset with the matching form everywhere, including `audit`

## Test runner

- **`playwright.config.*` or `@playwright/test` in devDependencies** → Playwright preset
- **`vitest.config.*` or `vitest` in devDependencies** → Vitest preset
- **`jest.config.*`, a `jest` key in package.json, or `jest` in devDependencies** → Jest preset
- **Playwright and a unit runner both present** → Playwright for acceptance tests; the unit runner stays in `check`
- **None** → ask which to add; installing one is a change the requester approves

## Commands

- **`check`** → the scripts CI runs, minus browser tests: format check, lint, typecheck, unit tests, build
  - Read `.github/workflows/*` when present; it's the best record of what must pass
  - A project script named `check` or `verify` that already does this → use it as is
- **`check_full`** → `check` plus every slower suite: e2e, visual, accessibility
- **`tests.run`** → keep `{files}` and `{grep}`; kit fills and shell-quotes both
- **`audit`** → leave out when the project has no runtime dependencies

## App

- **`app.serve`** → a production build served on a fixed port, like `pnpm build && pnpm start --port 3100`
  - Pick a port nothing else in the project uses; `app.url` uses the same port
  - Services the app needs (database, stand-ins) must already be running, or `serve` starts them
- **`app.env`** → what tells the test runner to reuse that server instead of starting one; for Playwright, `REUSE_SERVER=1` read by `webServer.reuseExistingServer`
- **Pages behind sign-in** → add `--load-storage=<state file>` to `screenshots`, and say how to create the file

## Format and lint on write

- **Prettier installed** → `format` with the extensions it handles in this project
- **ESLint installed** → `lint` with the extensions in its config
- **Biome** → one command for both: `format.run` as `node_modules/.bin/biome check --write {file}`, and no `lint`
- Call binaries through `node_modules/.bin/`; it starts faster than the package manager
