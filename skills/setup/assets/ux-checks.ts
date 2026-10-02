// kit's UX checks, copied by /kit:setup. UX probes import these to check a route the same way
// on every build; see kit's review-ux checklist for which failures block.
import type { Page } from '@playwright/test';

export type UxCheck = 'side scroll' | 'tap target' | 'clipped text' | 'focus' | 'axe';
export type UxProblem = { check: UxCheck; detail: string };

const MIN_TAP_PX = 44;

const INTERACTIVE = [
  'a[href]',
  'button',
  'input:not([type=hidden])',
  'select',
  'textarea',
  'summary',
  '[role=button]',
  '[role=link]',
  '[role=checkbox]',
  '[role=switch]',
  '[role=tab]',
  '[role=menuitem]',
  '[role=option]',
  "[tabindex]:not([tabindex='-1'])",
].join(',');

// Every check that needs no interaction: run it at 390px in light and in dark.
export async function uxProblems(page: Page): Promise<UxProblem[]> {
  return [
    ...(await sideScroll(page)),
    ...(await smallTapTargets(page)),
    ...(await clippedText(page)),
    ...(await axeProblems(page)),
  ];
}

export async function sideScroll(page: Page): Promise<UxProblem[]> {
  const overflowPx = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  return overflowPx > 0
    ? [{ check: 'side scroll', detail: `the page is ${overflowPx}px wider than the window` }]
    : [];
}

// Visible controls under 44px either way. Links inside running text are exempt (WCAG 2.5.5).
export async function smallTapTargets(page: Page, minPx = MIN_TAP_PX): Promise<UxProblem[]> {
  const found = await page.evaluate(
    ({ selector, minPx }) =>
      [...document.querySelectorAll<HTMLElement>(selector)].flatMap((element) => {
        const box = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        const isHidden = box.width === 0 || box.height === 0 || style.visibility === 'hidden';
        const isInlineLink = element.tagName === 'A' && style.display === 'inline';
        if (isHidden || isInlineLink || (box.width >= minPx && box.height >= minPx)) return [];
        const name =
          element.getAttribute('aria-label') ||
          element.textContent?.trim().slice(0, 40) ||
          element.tagName.toLowerCase();
        return [`"${name}" is ${Math.round(box.width)}×${Math.round(box.height)}px`];
      }),
    { selector: INTERACTIVE, minPx },
  );
  return found.map((detail) => ({ check: 'tap target', detail }));
}

// Elements whose own text is cut off: an ellipsis, or overflow hidden past their box.
export async function clippedText(page: Page): Promise<UxProblem[]> {
  const found = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>('body *')].flatMap((element) => {
      const ownText = [...element.childNodes]
        .filter((node) => node.nodeType === Node.TEXT_NODE)
        .map((node) => node.textContent ?? '')
        .join('')
        .trim();
      if (!ownText || element.offsetParent === null) return [];
      const style = getComputedStyle(element);
      const hidesOverflow = ['hidden', 'clip'].includes(style.overflowX);
      const isCut = element.scrollWidth > element.clientWidth + 1;
      const isClamped = style.webkitLineClamp !== 'none' && style.webkitLineClamp !== '';
      const isClampCut = isClamped && element.scrollHeight > element.clientHeight + 1;
      return (hidesOverflow && isCut) || isClampCut ? [`"${ownText.slice(0, 60)}"`] : [];
    }),
  );
  return found.map((detail) => ({ check: 'clipped text', detail }));
}

// Where focus went after an action: the page body means keyboard users lost their place.
export async function focusLost(page: Page): Promise<UxProblem[]> {
  const activeTag = await page.evaluate(() => document.activeElement?.tagName ?? 'BODY');
  return activeTag === 'BODY' || activeTag === 'HTML'
    ? [{ check: 'focus', detail: 'focus fell to the page body' }]
    : [];
}

// axe's WCAG A and AA rules, contrast included; needs @axe-core/playwright installed.
export async function axeProblems(page: Page): Promise<UxProblem[]> {
  const moduleName = '@axe-core/playwright';
  const axe = await import(moduleName).catch(() => {
    throw new Error(`UX checks need ${moduleName}: add it to devDependencies`);
  });
  const results = await new axe.default({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
  return results.violations.map((violation: { id: string; nodes: unknown[] }) => ({
    check: 'axe',
    detail: `${violation.id} on ${violation.nodes.length} element(s)`,
  }));
}
