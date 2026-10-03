# Bringing an existing app into the architecture

An app with code already in place adopts the architecture in two steps. First, the architecture spec builds the guide and the checks, with today's code baselined so the check stays green. Then each move is its own spec, built and reviewed like any feature, until the baseline is empty.

## Read before mapping

- **Every top-level source folder** → what each holds today, and which of the five homes it maps to
- **Each module's files** → for each one: what it exports, who imports it, and how long it is (`wc -l`)
- **Files over the line cap** → list the jobs inside each one: use cases, rules, queries, outside calls, streaming, formatting
- **Imports between modules** → which module calls which; a pair that calls both ways means one of them owns a noun that belongs to the other

## Mapping a file

Use the guide's question tree on the code, not the file name:

- **A file holding one kind of code** → one line: its path, then its new home
- **A file mixing kinds** → one line per destination, naming the functions that go there; the rules go to `domain/`, the queries to `infra/`, each exported action to its own `use-cases/` file
- **A folder of mixed things, like `lib/` or `utils/`** → each file on its own: pure goes to lib, I/O to platform, business words to their module
- **Shared infrastructure scattered through modules** → one platform capability; two database pools or secret reads in several modules become one `platform/db` and one `platform/env.ts`
- **A module holding two nouns that share no rules** → split it, and name both new modules
- **Tests** → follow the code they test; a test that mocks storage to reach a rule becomes a plain test of that rule in `domain/`

## moves.md

`specs/<id>/moves.md`, beside the architecture spec. One section per move, in the order they'll run:

```markdown
# Moves

## 1. One database pool and session in platform

- `src/lib/app-pool.ts` → `src/platform/db/pool.ts`
- `src/modules/auth/data/limits.ts` → its pool goes; queries use `src/platform/db`
- `src/modules/firms/server.ts` → `withFirmSession`, `holdFirmSession` to `src/platform/session/ctx.ts`

## 2. Split agents into agent-runs and inbox

- …
```

- **Order** → platform first, since every module depends on it; then module splits; then each module's interior, biggest file first
- **Size** → a move fits one spec: a few files, or one module's interior; bigger moves split
- **Every file the baseline lists** → appears in some move, so the list can reach empty

## The baseline

- **Turning it on** → set `"baseline": ".claude/kit/architecture-baseline.json"` in the config's `architecture`, run `check_shape.py --write-baseline`, and commit the file
- **What it allows** → listed files keep their place, and keep their length as long as they don't grow; any new file meets the shape
- **Lint** → list the files that break the lint today in `architectureLegacy([...])`; they get warnings instead of errors
- **After each move** → its spec's last task removes the moved files from `architectureLegacy` and reruns `--write-baseline`, so both lists only shrink

## A move spec

Started with `/kit:build <the move's heading>` once the architecture spec is done. Its behaviors are what stays true and what the checks say:

- **The app still does what it did** → the existing acceptance and e2e tests pass, unchanged
- **The moved files** → pass lint and `check_shape.py` with no baseline or legacy entry
- **The baseline and legacy list** → lose every moved file
