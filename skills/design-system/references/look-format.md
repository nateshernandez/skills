# look.md format

`docs/design/look.md` records where the app's look came from: the screens it was measured from, what was measured, and the tokens proposed from them. The foundations spec's decisions cite it; the design guide takes its token values from it. Keep it ≤ 150 lines.

## Shape

```markdown
# Look

<One line: the look in plain words, and the apps it draws from.>

## Sources

- **Linear: issue list grouped by status, dark** → [Mobbin](https://mobbin.com/screens/<id>)
- **Stripe: customer detail with payments table, light** → [Mobbin](https://mobbin.com/screens/<id>)

## Measured

Estimates from compressed previews, rounded to the 4px grid.

- **Tones** → sidebar one step behind content in both themes: light `#f3f3f3` to `#fdfdfd`, dark `#080808` to `#0f0f0f` (Linear, Vercel)
- **Borders** → 1px hairlines; dividers between money rows, whitespace between issue rows (Stripe, Linear)
- **Accent** → indigo on the primary button, links, and focus only; under 1% of pixels (Linear, Mercury)
- **Type** → 13px body and tables, 20px/600 page titles, mono only for IDs (Linear, Vercel)
- **Density** → 28px controls, 36px rows, 240px sidebar
- **Radii** → 4px badges, 6px controls, 8px cards, 12px dialogs and the content panel
- **Shadows** → floating layers only; dark mode uses a lighter surface instead
- **Status** → text on a tinted fill for badges; a dot beside plain text in dense lists

## Proposed tokens

- **`--background`** → light `oklch(0.991 0 0)`, dark `oklch(0.174 0.004 286)`: the content canvas
- **`--muted-foreground`** → light `oklch(0.531 0.015 286)`, dark `oklch(0.709 0.014 286)`: secondary text; 5.1:1 on background
- **`--success` on `--success-bg`** → ...: paid, done, money in

## Decided against

- **Mercury's navy-tinted greys** → warmer and more finance-like than the product wants
```

## Rules

- **A measured value** → names the source screens in brackets; one with no source is a guess, so mark it `(chosen)`
- **A proposed colour** → each theme the app ships, in the project's colour format, with the contrast of its main pair
- **Token names** → the project's existing names first, then shadcn's (`background`, `foreground`, `card`, `muted`, `primary`, `border`, `input`, `ring`), then `<status>` and `<status>-bg` for status colours, so `check_tokens.py` finds the pairs by name
- **Decided against** → the strongest alternatives, each one line; they become the specs' Alts
