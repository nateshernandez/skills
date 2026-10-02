# Recipe: Next.js, Tailwind 4, shadcn

How the design foundations and core screens specs get built in a Next.js app styled with Tailwind 4 and shadcn. The planner reads this beside the spec; each section is one piece of the plan. It comes from btnext's design system, where every piece below ran in production.

## Tokens

- **Where** → `src/app/globals.css` only, and the config's `design.tokens` names it: light values in `:root`, dark in `.dark`, and Tailwind classes from `@theme inline { --color-<token>: var(--<token>); }`
- **Names** → shadcn's (`background`, `foreground`, `card`, `popover`, `primary`, `secondary`, `muted`, `accent`, `border`, `input`, `ring`, `sidebar-*`) plus `<status>` and `<status>-bg` for success, warning, danger, and info
- **Values** → from `docs/design/look.md`, in `oklch()`; `check_tokens.py` checks every pair kit finds by name, plus the config's `design.contrast`
- **Scale** → `@theme` sets the type scale (`--text-xs` … `--text-2xl`), radii (`--radius-sm` … `--radius-xl`), and one `--shadow-popover`; spacing stays Tailwind's 4px steps
- **Touch** → controls use the `pointer-coarse:` variant to reach 44px, like `h-7 pointer-coarse:h-11`

## Theme without a flash

A blocking script sets `.dark` before the first paint; `beforeInteractive` doesn't block, and an inline script needs `dangerouslySetInnerHTML`.

```js
// public/theme.js: runs in <head> before first paint, so the page never flashes the wrong theme.
(function () {
  var query = window.matchMedia('(prefers-color-scheme: dark)');
  function apply() {
    var stored = null;
    try {
      stored = localStorage.getItem('theme');
    } catch {
      // Storage blocked; follow the operating system.
    }
    var isDark = stored === 'dark' || (stored !== 'light' && query.matches);
    document.documentElement.classList.toggle('dark', isDark);
  }
  apply();
  query.addEventListener('change', apply);
})();
```

- **Root layout** → `<html suppressHydrationWarning>` and `<head><script src="/theme.js" /></head>`; turn off `@next/next/no-sync-scripts` for `src/app/layout.tsx` only
- **The choice** → a client component writes `localStorage.theme` as `light`, `dark`, or `system` (only those three) and re-applies in `useLayoutEffect`

## Dev-only gallery

```ts
// next.config.ts: `*.dev.tsx` route files exist only on the dev server, so nothing from the gallery ships.
import type { NextConfig } from 'next';
import { PHASE_DEVELOPMENT_SERVER } from 'next/constants';

const PAGE_EXTENSIONS = ['tsx', 'ts', 'jsx', 'js'];

export default function nextConfig(phase: string): NextConfig {
  const isDevServer = phase === PHASE_DEVELOPMENT_SERVER;
  return { pageExtensions: isDevServer ? [...PAGE_EXTENSIONS, 'dev.tsx'] : PAGE_EXTENSIONS };
}
```

- **Routes** → `src/app/design/page.dev.tsx`, `foundations/page.dev.tsx`, `components/page.dev.tsx`, then `layouts/<name>/` and `patterns/<name>/`; set `design.gallery` to `/design`
- **Registry** → `GALLERY_PAGES` in `src/app/design/_gallery/gallery-pages.ts` lists every page; the index, the axe scan, and any screenshot test read it
- **Samples** → gallery-only code and sample data live in `src/app/design/_gallery/`; product routes never import it
- **Production** → an acceptance test runs `pnpm start` and expects `/design` to be not found

## Components

- **Kit** → `pnpm dlx shadcn add <name>` into `src/components/ui/`, restyled to the tokens and density; destructive and link buttons need the danger and link tokens, since stock shadcn fails contrast
- **Layouts** → `src/components/layouts/`; **patterns** → `src/components/patterns/`; both take content as props and hold no sample data
- **Notices** → a provider in the root layout, so a notice outlives the navigation its action caused; code raises them through one hook
- **Focus** → one helper that moves focus to a neighbour when a focused row, chip, or card leaves

## Drift lint

`no-restricted-syntax` in `eslint.config.mjs`, for `src/**/*.{ts,tsx}` except `src/components/ui/**`. Every message names the fix and the guide, so an agent corrects itself on the write.

```js
const DESIGN_GUIDE = 'docs/design/guide.md';
const PALETTE = 'slate gray zinc neutral stone red orange amber yellow lime green emerald teal cyan sky blue indigo violet purple fuchsia pink rose'.split(' ');

function designDriftSelectors() {
  const colour = String.raw`\[(color:)?(#[0-9a-fA-F]{3,8}|(rgba?|hsla?|oklch|oklab|lab|lch|hwb|color)\()`;
  const size = String.raw`\[[^\]\s]*\d(px|rem|em)\b`;
  const styleColour = String.raw`(#[0-9a-fA-F]{3,8}\b|\b(rgba?|hsla?|oklch|oklab|lab|lch|hwb|color)\()`;
  const styleSize = String.raw`\d(px|rem|em)\b`;
  const palette = String.raw`(^|[\s:!])-?(bg|text|border(-[xytrblse])?|ring(-offset)?|outline|divide|fill|stroke|from|via|to|decoration|accent|caret|shadow|placeholder)-(white|black|(${PALETTE.join('|')})-(50|[1-9]00|950))(?![\w-])`;
  const colourMessage = `Raw colour: use a colour token class (bg-card, text-muted-foreground, text-danger) or var(--token) in style. See ${DESIGN_GUIDE}.`;
  const paletteMessage = `Tailwind palette colour: use a colour token class instead, so the colour follows light and dark. See ${DESIGN_GUIDE}.`;
  const sizeMessage = `Arbitrary size: use the theme scale (text-sm, p-2, h-7, rounded-md) or var(--token) in style. See ${DESIGN_GUIDE}.`;
  const strings = (pattern) => [`Literal[value=/${pattern}/]`, `TemplateElement[value.raw=/${pattern}/]`];
  const classNamed = String.raw`/class(es|name)?$/i`;
  const classContext = `:matches(JSXAttribute[name.name=${classNamed}], CallExpression[callee.name=/^(cn|cva|clsx|cx|twMerge)$/], VariableDeclarator[id.name=${classNamed}], Property[key.name=${classNamed}])`;
  const inClassStrings = (pattern) => strings(pattern).map((node) => `${classContext} ${node}`);
  const inStyle = (pattern) => strings(pattern).map((node) => `JSXAttribute[name.name="style"] ${node}`);
  const controls = {
    button: 'Button from "@/components/ui/button"',
    input: 'Input from "@/components/ui/input" (Checkbox or Switch for toggles)',
    select: 'Select from "@/components/ui/select"',
    textarea: 'Textarea from "@/components/ui/textarea"',
  };
  return [
    ...strings(colour).map((selector) => ({ selector, message: colourMessage })),
    ...inStyle(styleColour).map((selector) => ({ selector, message: colourMessage })),
    ...inClassStrings(palette).map((selector) => ({ selector, message: paletteMessage })),
    ...strings(size).map((selector) => ({ selector, message: sizeMessage })),
    ...inStyle(styleSize).map((selector) => ({ selector, message: sizeMessage })),
    ...Object.entries(controls).map(([tag, component]) => ({
      selector: `JSXOpeningElement[name.name="${tag}"]`,
      message: `Native <${tag}>: use ${component}, which carries the theme's size, focus, and states. See ${DESIGN_GUIDE}.`,
    })),
  ];
}
```

- **One rule, many blocks** → a later block's `no-restricted-syntax` replaces earlier ones for the same files, so every block that sets it spreads `designDriftSelectors()` in too
- **Brand marks** → a third-party logo keeps its owner's fixed SVG `fill`; lint allows `fill` attributes, so review keeps this to logos

## Checks

- **Routes** → `tests/routes.ts` lists every app route; an axe test scans each, and every `GALLERY_PAGES` entry, in light and dark (`page.emulateMedia({ colorScheme })`, or the stored theme)
- **axe** → `@axe-core/playwright` with tags `wcag2a` and `wcag2aa`; the same package `tests/kit/ux-checks.ts` uses
- **Gallery tests** → a Playwright project against `next dev`, since the gallery exists only there; reuse the URL in `.next/dev/lock` when a dev server is already running
- **Visual baselines** → off by default (the foundations spec's decision); to opt in, `toHaveScreenshot` on each gallery page at 1280px in both themes, Linux Chromium only, plus a script that accepts new baselines

## Decision records

The build's codify step records these, each citing its code:

- **Tokens only in `globals.css`**, named as above, with the look's density
- **Theme class from a blocking script**, system by default
- **Dev-only gallery** through `pageExtensions` and the page registry
- **Drift lint** on raw colours, palette colours, arbitrary sizes, and native controls
- **Layouts from the guide's page-type tree**, and patterns as shared pieces
