# Recipe: Next.js and React

How the architecture spec gets built in a Next.js app with the App Router and React 19, in TypeScript. The planner reads this beside the spec; each section is one piece of the plan, and the guide's `<…>` are filled from it. It comes from btnext, where layers and module entries held up and module interiors didn't: one entry file grew to 2,491 lines, and its tests needed 368 mock setups.

## Homes

- **`<routes folder>`** → `src/app`: `page.tsx`, `layout.tsx`, `route.ts`, and Next's special files; no other code, except a dev gallery's `_gallery/` from the design system
- **`<modules folder>`** → `src/modules`
- **`<components folder>`** → `src/components`: `ui/` (shadcn), `layouts/`, `patterns/`, `hooks/`, as the design system recipe lays out
- **`<platform folder>`** → `src/platform`: `db/`, `session/`, `env.ts`, then a folder per outside service (`ai/`, `email/`) and `http/` for request helpers; every file starts with `import 'server-only'`
- **`<lib folder>`** → `src/lib`: pure TypeScript that runs anywhere, like `result.ts`, `format.ts`, `text-diff.ts`
- **Imports** → the `@/` alias for anything outside the current module; relative paths inside it

## Module

- **`<client entry>`** → `index.ts`: re-exports components, types, and client-safe constants
- **`<server entry>`** → `server.ts`: `import 'server-only'`, then re-exports of use cases; nothing defined here
- **`<form adapters>`** → `actions.ts`: `'use server'` functions that build who's asking, call a use case, and revalidate
- **`<component file kinds>`** → `*.tsx` components, `use-*.ts` hooks, `*-state.ts` pure reducers
- **`<use case signature>`** → `export async function changeTicketStatus(ctx: Ctx, input: unknown): Promise<Result<…>>`
- **`<lint file>`** → `eslint/architecture.mjs`
- **`<context type and builder>`** → `Ctx`, built by `withPageCtx`, `withActionCtx`, or `withRouteCtx`
- **Tables** → `infra/tables.ts`, with no `server-only` so drizzle-kit can load it; a foreign key to another module's table goes in the migration SQL, not an import
- **Unit tests** → next to the file they test, as `<name>.test.ts`; kit counts them as that file

## Who's asking

`src/platform/session/` arrives with the first feature that signs people in. Until then use cases take what they need as input.

```ts
// src/platform/session/ctx.ts
import 'server-only';
import { redirect } from 'next/navigation';
import { db, type Transaction } from '@/platform/db';
import { readSignedIn, type Actor } from './signed-in';

/** Who's asking, and the transaction their request runs in. Built at the edge, passed down. */
export type Ctx = { tx: Transaction; actor: Actor };

async function withCtx<T>(work: (ctx: Ctx) => Promise<T>): Promise<{ value: T } | null> {
  const actor = await readSignedIn();
  if (!actor) return null;
  return { value: await db.transaction((tx) => work({ tx, actor })) };
}

/** For pages: signed out goes to sign-in. */
export async function withPageCtx<T>(work: (ctx: Ctx) => Promise<T>): Promise<T> {
  const result = await withCtx(work);
  if (!result) redirect('/sign-in');
  return result.value;
}
```

- **One helper per edge** → `withPageCtx` redirects, `withActionCtx` returns `{ ok: false, error }` with the signed-out message, `withRouteCtx` answers 401
- **Tenancy** → set it inside the transaction (`set_config` for row-level security) where `withCtx` opens it, so no use case can forget
- **Work after the response** (`after()`) → hold the verified actor before the response ends and open a new transaction from it; never reuse the request's

## Examples

```ts
// src/lib/result.ts
export type Result<T = undefined> = { ok: true; value: T } | { ok: false; error: string };
```

```ts
// src/modules/tickets/domain/ticket-status.ts: rules and schemas; pure, so the client may import it
import { z } from 'zod';
import type { Result } from '@/lib/result';

export const TICKET_STATUSES = ['todo', 'doing', 'done'] as const;
export type TicketStatus = (typeof TICKET_STATUSES)[number];
export const changeStatusSchema = z.object({ ticketId: z.uuid(), status: z.enum(TICKET_STATUSES) });

/** A done ticket reopens to Todo only, so its history reads as a reopening. */
export function planStatusMove(from: TicketStatus, to: TicketStatus): Result<{ isReopening: boolean }> {
  if (from === 'done' && to === 'doing') return { ok: false, error: 'Reopen the ticket to Todo first.' };
  return { ok: true, value: { isReopening: from === 'done' } };
}
```

```ts
// src/modules/tickets/infra/ticket-queries.ts: storage only; queries named for what they return
import 'server-only';
import { eq } from 'drizzle-orm';
import type { Ctx } from '@/platform/session';
import type { TicketStatus } from '../domain/ticket-status';
import { tickets } from './tables';

export async function findTicketStatus({ tx }: Ctx, ticketId: string): Promise<TicketStatus | null> {
  const [row] = await tx.select({ status: tickets.status }).from(tickets).where(eq(tickets.id, ticketId));
  return row?.status ?? null;
}
```

```ts
// src/modules/tickets/use-cases/change-ticket-status.ts: parse, load, decide, store, return
import 'server-only';
import type { Result } from '@/lib/result';
import type { Ctx } from '@/platform/session';
import { changeStatusSchema, planStatusMove } from '../domain/ticket-status';
import { findTicketStatus, saveStatusMove } from '../infra/ticket-queries';

export async function changeTicketStatus(ctx: Ctx, input: unknown): Promise<Result> {
  const parsed = changeStatusSchema.safeParse(input);
  if (!parsed.success) return { ok: false, error: parsed.error.issues[0].message };
  const current = await findTicketStatus(ctx, parsed.data.ticketId);
  if (!current) return { ok: false, error: 'That ticket no longer exists.' };
  const move = planStatusMove(current, parsed.data.status);
  if (!move.ok) return move;
  await saveStatusMove(ctx, { ...parsed.data, isReopening: move.value.isReopening });
  return { ok: true, value: undefined };
}
```

```ts
// src/modules/tickets/actions.ts: form and button adapters
'use server';
import { revalidatePath } from 'next/cache';
import type { Result } from '@/lib/result';
import { withActionCtx } from '@/platform/session';
import { changeTicketStatus } from './server';

export async function changeTicketStatusAction(input: { ticketId: string; status: string }): Promise<Result> {
  const result = await withActionCtx((ctx) => changeTicketStatus(ctx, input));
  if (result.ok) revalidatePath(`/tickets/${input.ticketId}`);
  return result;
}
```

```tsx
// src/app/tickets/[ticketId]/page.tsx: build who's asking, call use cases, compose modules
import { withPageCtx } from '@/platform/session';
import { TicketDetail } from '@/modules/tickets';
import { readTicket } from '@/modules/tickets/server';
import { AgentThread } from '@/modules/agent-runs';
import { readAgentThread } from '@/modules/agent-runs/server';

export default async function TicketPage({ params }: { params: Promise<{ ticketId: string }> }) {
  const { ticketId } = await params;
  const [ticket, thread] = await withPageCtx((ctx) => Promise.all([readTicket(ctx, ticketId), readAgentThread(ctx, ticketId)]));
  return (
    <TicketDetail ticket={ticket}>
      <AgentThread thread={thread} />
    </TicketDetail>
  );
}
```

```tsx
// src/modules/tickets/components/ticket-status-menu.tsx: a client leaf that changes data
'use client';
import { useState, useTransition } from 'react';
import { changeTicketStatusAction } from '../actions';
import type { TicketStatus } from '../domain/ticket-status';

export function TicketStatusMenu({ ticketId, status }: { ticketId: string; status: TicketStatus }) {
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  function choose(next: TicketStatus) {
    startTransition(async () => {
      const result = await changeTicketStatusAction({ ticketId, status: next });
      setError(result.ok ? null : result.error);
    });
  }
  // …renders the menu, disabled while pending, with the error under it
}
```

```ts
// src/modules/agent-runs/components/use-run-events.ts: transport the actions can't do lives in a hook
import { useEffect, useReducer } from 'react';
import { reduceRunEvents, startingRunEvents } from './run-events-state';

export function useRunEvents(ticketId: string) {
  const [events, dispatch] = useReducer(reduceRunEvents, startingRunEvents);
  useEffect(() => {
    const source = new EventSource(`/tickets/${ticketId}/agent`);
    source.onmessage = (message) => dispatch({ kind: 'received', data: message.data });
    return () => source.close();
  }, [ticketId]);
  return events;
}
```

## UI rules

The guide's UI code section, and `react-components.md`:

- **Server first** → components render on the server; `'use client'` goes on the smallest leaf with state, effects, or browser events
- **Reads** → the page calls use cases and passes props shaped for the view; components never fetch app data, and server actions never read
- **Changes** → one way: a server action from the module's `actions.ts`; forms through `useActionState`, buttons through `useTransition`; the action revalidates
- **What actions can't do** → streaming, keepalive saves, and uploads use `fetch` or `EventSource` inside a `use-*.ts` hook, against a `route.ts` that calls a use case
- **Effects** → only to sync with something outside React; derive values while rendering; move focus and call parent callbacks in the event handler
- **Files** → one exported component per file, named after it; the name says the kind: `*.tsx`, `use-*.ts`, `*-state.ts`, `*-provider.tsx` holding one context
- **Props** → at most 7; past that, pass `children` or slots; context only for state many distant leaves share

## Lint

The architecture skill copies `architecture.mjs` into the spec's folder beside this recipe; the build copies it to `eslint/architecture.mjs` and spreads it after Next's configs. It needs `eslint-plugin-boundaries` 7 or later; `import/no-cycle` comes with `eslint-config-next`.

```js
// eslint.config.mjs
import { architectureBlocks, architectureLegacy } from './eslint/architecture.mjs';

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  ...architectureBlocks,
  // Files from before the architecture; each move spec removes its own. Empty in a new app.
  ...architectureLegacy([]),
]);
```

- **Design drift lint too** → `no-restricted-syntax` in a later block replaces the earlier one, so every block setting it spreads `architectureSyntax()` in as well
- **Legacy files** → their findings stay as warnings; a `check` with `--max-warnings 0` needs them left out of that run's count
- **Proof** → acceptance tests write a violating file to a temp path under `src/`, lint it, expect the message, and delete it

## Shape

The config's `architecture` block:

```json
"architecture": {
  "guide": "docs/architecture.md",
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
  "max_lines": 250
}
```

- **Existing app** → add `"baseline": ".claude/kit/architecture-baseline.json"` and run `check_shape.py --write-baseline`
- **`<max lines>`** → 250; shadcn's generated files are exempt, since they're upstream code

## Tests

- **Domain and lib** → Vitest, plain calls, no mocks; every rule's branches
- **Use cases** → against the test database, never mocked queries: `src/platform/db/test-ctx.ts` exports `withTestCtx(work)`, which opens a transaction on the compose Postgres, runs the test, and rolls back
- **Components** → Testing Library with props; client hooks with their reducer tested apart in `*-state.test.ts`
- **Outside services** → a stand-in served locally (like a model or auth stand-in in compose), not a module mock

## Decision records

The build's codify step records these, each citing its code:

- **Five homes and one-way imports**, with the lint that enforces them
- **The module shape**: entries, flat folders, inward imports, and the shape check
- **Use cases take who's asking**, built once per edge in `src/platform/session`
- **One way to change data**: server actions; `fetch` only in hooks, for what actions can't do
- **Use cases tested against a real database**, domain without mocks
