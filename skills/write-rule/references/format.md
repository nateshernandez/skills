# Rule file format

## Rules vs everything else

- **A tool can check it** → its config: `eslint.config.mjs`, `tsconfig.json`, `ruff.toml`, `pyrightconfig.json`
  - ESLint covers most TypeScript architecture boundaries: `no-restricted-imports`, `no-restricted-syntax`
  - _Because:_ tools enforce; a rule may point at the tool, never restate it
- **It applies whenever certain files are touched** → a rule
- **It's a multi-step job started by a task** → a skill (write-skill)
- **It's a project fact (commands, layout)** → `CLAUDE.md`
- **It's an architecture choice and its reasons** → a decision record (write-decision); rules enforcing it cite the record

## How rules load

- **`paths:` set** → the rule loads when a matching file is read or edited
- **`paths:` set, file is being created** → the rule does **not** load
  - Verified 2026-09-25: 4/4 headless runs creating a new matching file never loaded the rule
  - So creation-time standards must also be linked from the skill or template that creates the file
- **No `paths:`** → loads in every session; allowed only with `<!-- always-on: <reason> -->`
- All rules matching a file load together, so their combined size is the real cost

## File shape

```markdown
---
paths:
  - "**/*.py"
---

# Python naming

Names are for a reader who only sees the signature.

- **Naming a variable or argument** → use the domain's word, spelled out
  - _Because:_ `data`, `tmp`, `val` describe nothing
  - ✗ `disc_val` ✓ `discount_value`
```

- **File name** → `<scope>-<concern>.md`, kebab-case: `python-naming.md`, `skill-script-output.md`
- **Title** → `# <Scope> <concern>`, the concern not just the language
- **Principle line** → one line under the title; the idea every rule follows from
- **Rules** → the only other content; no `##` sections, tables, code blocks, or numbered steps

## Rule shape

- **Situation** (bold) → something you'd notice mid-task: "About to write a comment", not "Write good code"
- **Action** (after `→`) → what to do, in the imperative
- **Because** (nested, required, exactly one) → why; if you can't write one, cut the rule
- **Example** (nested, optional, at most one) → `✗ <bad> ✓ <good>` on a single line

## Limits

- One concern per file
- `paths:` required (or an always-on comment with a reason)
- Principle line: ≤ 25 words
- ≤ 8 rules per file
- ≤ 40 non-blank lines after the frontmatter
- Situation, action, and Because: ≤ 20 words each
