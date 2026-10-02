---
paths:
  - "**/*.ts"
---

# TypeScript checks

`biome.json` and `tsconfig.json` at the repo root define what counts as a problem for the TypeScript kit copies into projects.

- **Finished editing a TypeScript file** → run `npm run format`, then `npm run check`, until clean
  - _Because:_ CI runs the same `biome ci` and `tsc`; clean here means green there
- **A check fires and the code is right** → suppress that one rule with `// biome-ignore <rule>: <reason>`
  - _Because:_ the reason turns a suppression into a documented decision
- **Tempted to loosen `biome.json` or `tsconfig.json`** → ask the user first
  - _Because:_ every asset kit ships is held to the same config
- **The file imports a package** → import only what the projects it lands in already have, or say in a comment which devDependency it needs
  - _Because:_ an asset is copied into someone else's project, where an unmet import fails their build
