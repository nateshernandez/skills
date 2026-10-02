---
id: <id>
status: draft
size: L
---

# Design foundations

Every screen draws from one theme in light and dark, agents see their UI in seconds, and checks catch drift.

## Decide

- **<n>.D1 Look** → <tones, accent and where it shows, borders>; drawn from <apps in look.md>
  - _Alt:_ <the strongest look decided against in look.md> (design lens)
- **<n>.D2 Typefaces** → <UI face>; <mono face> for IDs and codes; tabular figures for numbers in columns
  - _Alt:_ <another face and its cost, such as a font download> (tech lens)
- **<n>.D3 Density** → <body px> text, <control px> controls, <row px> rows, 4px spacing grid; controls 44px on touch screens
  - _Alt:_ <roomier or denser numbers, and what fits on screen> (product lens)
- **<n>.D4 First visit theme** → follow the operating system; a choice of light, dark, or system
  - _Alt:_ <light or dark> by default; striking, but ignores the visitor's setting (UX lens)
- **<n>.D5 Catching visual drift** → lint, contrast checks, axe, and screenshot review; no committed image baselines
  - _Alt:_ gallery screenshots diffed against baselines; catches more, needs re-accepting on every change (quality lens)

## Behaviors

- **<n>.B1 Developer opens the gallery on the dev server** → an index linking Foundations and Components pages
- **<n>.B2 Anyone opens the gallery on a production build** → not found page; nothing from the gallery ships
  - _Because:_ security lens; the gallery is a dev tool, not product surface
- **<n>.B3 Developer opens Foundations** → named swatches for every colour token, type scale, spacing, radii, and elevation
- **<n>.B4 Developer opens Components** → every component in each variant and state: default, disabled, invalid, loading
- **<n>.B5 Foundations shows status colours** → success, warning, danger, info, each as text on its tint, in both themes
- **<n>.B6 Visitor picks light, dark, or system** → it applies at once, survives reload, and never flashes the wrong theme
- **<n>.B7 Accessibility check runs** → every app and gallery route passes axe in light and dark
- **<n>.B8 Keyboard user tabs through Components** → every control shows a visible focus ring in both themes
- **<n>.B9 Gallery at phone width** → nothing scrolls sideways; every control is at least 44px tall on a touch screen
- **<n>.B10 Code uses a raw colour, arbitrary size, or a native control the kit wraps** → lint fails, naming what to use
- **<n>.B11 Anyone opens a route that doesn't exist** → a not-found page in the app's look, with a link home
- **<n>.B12 Agent opens the design guide** → tokens and their uses, components, and how to look at and check UI

## Not doing

- Page layouts and interaction patterns; the core screens spec
- Domain layouts such as boards, timesheets, or invoices, until a feature needs one
- Charts and data visualisation colours
- Marketing pages

## Looks like

![Specimen, light](screens/specimen-desktop-light.png)
![Specimen, dark](screens/specimen-desktop-dark.png)
![Specimen at phone width](screens/specimen-mobile-light.png)
