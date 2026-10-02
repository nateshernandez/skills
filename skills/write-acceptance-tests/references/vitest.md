# Acceptance tests in Vitest or Jest

Tests read like the spec: one `test()` per behavior, titled with its full ID (`1.B1`, not `B1`), asserting what a caller of the public interface would observe. Jest uses the same shape without the import.

```ts
import { describe, expect, test } from "vitest";
import { createWaitlist } from "../../src/index";

describe("1 waitlist", () => {
  test("1.B1 Visitor joins with a valid email", async () => {
    const waitlist = createWaitlist();
    const result = await waitlist.join("b1@example.com");
    expect(result).toEqual({ status: "joined" });
    expect(await waitlist.has("b1@example.com")).toBe(true);
  });

  test('1.B2 Visitor joins with "abc"', async () => {
    const waitlist = createWaitlist();
    await expect(waitlist.join("abc")).rejects.toThrow(/valid email/i);
    expect(await waitlist.count()).toBe(0);
  });
});
```

## What to call

- **A library** → its public entry point, the one users import; never a module path below it
- **An HTTP service** → real requests to the running app (`fetch(process.env.KIT_APP_URL ?? baseURL)`), asserting status and body
- **A CLI** → run the built binary with `execa` or `child_process`, asserting exit code, stdout, and files written
- **Anything else** → the narrowest interface a user touches; if the plan names one, use that

## Data and time

- **Fresh state per test** → build it in the test or `beforeEach`; tests never depend on order
- **A delay or expiry is part of the behavior** → `vi.useFakeTimers()` (Jest: `jest.useFakeTimers()`), then advance past it
- **Rate limits and repeats** → loop in the test

## Titles

- The gate filters by title with `-t`, so the ID must be in the `test()` title itself, not only in `describe`
- A `describe` around a spec's tests is fine; keep the ID at the start of each test title
