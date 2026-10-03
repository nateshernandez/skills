---
paths:
  - "src/**/*.tsx"
  - "src/**/use-*.ts"
  - "src/**/*-state.ts"
---

# React components

Components render what they're given: pages bring the data, actions make the changes, and logic sits beside them in named files.

- **Writing a component** → a Server Component unless it needs state, effects, or browser events; then `'use client'` on that leaf
  - _Because:_ everything a client file imports joins the browser bundle
- **A component needs data** → the page calls a use case and passes props shaped for the view
  - _Because:_ one place loads data, so components stay easy to test and reuse
- **A component changes data** → call the module's server action: forms with `useActionState`, buttons with `useTransition`
  - _Because:_ one path for changes gives pending, errors, and revalidation the same way everywhere
- **Streaming, a keepalive save, or an upload** → `fetch` or `EventSource` in a `use-*.ts` hook, never in a component
  - _Because:_ transport hidden in a hook keeps the component about what it shows
- **Reaching for `useEffect`** → only to sync with something outside React; derive values in render, act in handlers
  - _Because:_ effects that copy state or notify parents add a render and a bug each
- **State with more than two moving parts** → a pure reducer in `<name>-state.ts`, tested on its own
  - _Because:_ a reducer reads as a list of what can happen, and tests without rendering
- **A second exported component, or more than 7 props** → split the file; pass `children` or slots instead
  - _Because:_ one component per file is found by its name; slots end prop drilling
- **State that many distant leaves share** → one context in a `<name>-provider.tsx`; otherwise pass props
  - _Because:_ the file name says where shared state lives
