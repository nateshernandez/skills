# Acceptance tests in Playwright

Tests read like the spec: one `test()` per behavior, titled with its full ID (`1.B1`, not `B1`), asserting what a person would see.

```ts
import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/waitlist");
});

test("1.B1 Visitor submits a valid email", async ({ page }) => {
  const email = `b1-${Date.now()}@example.com`;
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Join the waitlist" }).click();
  await expect(page.getByText("You're on the list")).toBeVisible();
  await expect(page.getByLabel("Email")).toBeHidden();
});

test('1.B2 Visitor submits "abc"', async ({ page }) => {
  await page.getByLabel("Email").fill("abc");
  await page.getByRole("button", { name: "Join the waitlist" }).click();
  await expect(page.getByText(/valid email/i)).toBeVisible();
});

test("1.B4 Viewed at 375px wide", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});
```

## Selecting and asserting

- **Selecting elements** → `getByRole`, `getByLabel`, `getByText`; never CSS classes or test IDs
  - _Because:_ any implementation that meets the spec should pass
- **Labels and button text** → copy the spec's words when it names them; otherwise pick plain ones and say so in the commit body
- **Layout behaviors** → `setViewportSize`, then assert on `scrollWidth` or `boundingBox()`

## Data and time

- **Unique data per run** → `Date.now()` in emails and names, so tests don't collide under `fullyParallel`
- **A browser timer gates the next step** → `page.clock.install()`, then `page.clock.runFor(ms)` past it
- **The server enforces the window (expiry, resend delay)** → age the stored timestamp through a test-only hook; never wait real time
- **Rate limits and repeats** → loop in the test

## Servers

- The gate puts a free port in `KIT_PORT`; let `webServer.port` and `use.baseURL` read it, so every gate gets a fresh server
- During review, `app.env` from the config is set (for example `REUSE_SERVER=1`), and `KIT_APP_URL` holds the shared app's URL
