# SKILL.md format

## Three parts, one job each

- **`description`** → routing only
  - `Use when:` + `Not when:`, ≤ 200 chars, no how-to
- **Body** (SKILL.md below the frontmatter) → what to do, readable in 30 seconds
  - ≤ 60 non-blank lines, fixed `##` sections, no paragraphs
- **Extras** → loaded on demand; any size, but every file must be linked from More
  - `references/`: material the agent reads to learn
  - `scripts/`: code the agent runs instead of following prose
  - `assets/`: files the agent copies into output (templates, boilerplate)

## Sections

- **`## Goal`** (required): one line, the outcome not the activity
  - Ask: "When this skill finishes well, what's true?"
- **`## In`** (required): bullets; mark "ask if missing"
  - Ask: "What does it need to start? What can it find itself?"
- **`## Out`** (required): bullets, each artifact and where it lands
  - Ask: "What does it hand back, and where?"
- **`## Flow`** (required): one `mermaid` flowchart, ≤ 10 nodes, nothing else
  - Ask: "Walk me through it. Where does it branch or loop?"
- **`## Rules`** (required, `none` allowed): `- **When** → do`, each with a nested `- *Because:*`
  - Ask: "Where does a naive attempt go wrong? Why?"
- **`## Done When`** (required): `- [ ]` checklist, each item checkable
  - Ask: "How would you check the work was right?"
- **`## Never`** (required, `none` allowed): ≤ 5 bullets
  - Ask: "What would make you revert this immediately?"
- **`## More`** (optional): bullets linking `references/`, `scripts/`, `assets/`

## Description questions

The router may be a human's session, an orchestrator, or a subagent. Write for all of them.

- **Use when:** "What task situation calls for this?" Describe the work, not who asks for it.
  - ✗ `Use when: user asks for release notes`
  - ✓ `Use when: release notes or a changelog are needed from git history`
- **Not when:** "Which other skill or task is this most likely to be confused with?" Name it.

## Where content goes

- Sentence of how-to → a Flow node, a rule, or a Done When item. If it fits none, drop it.
- Examples, API details, style guides, long lists → `references/<topic>.md`.
- Anything deterministic (parsing, formatting, querying) → `scripts/`.
- Flow needs more than ~8 nodes → it's two skills.

## Flow conventions

- `flowchart TD`; quote every label: `A["Do the thing"]`.
- Decisions are `{"Question?"}` with `-- yes -->` / `-- no -->` edges.
- Loops point back to an earlier node rather than repeating it.

## Rule shape

```markdown
- **Commit is chore/ci/test** → drop it
  - *Because:* users don't care
```

- The bold part is the situation; after `→` is the action.
- The Because line is required; if you can't write one, cut the rule.
- No tables anywhere in a skill.
