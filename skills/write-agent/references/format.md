# Agent file format

## Agents vs skills

- **Skill** → how: the procedure and its bar; runs in any context
- **Agent** → who and where: its own context, tools, fences, and model
- **Make an agent only when** → it needs independence (reviews), tool limits, or a clean context per run

## Fields

- **`name`** → matches the file name
- **`description`** → `Use when:` + `Not when:`, ≤ 200 chars; the orchestrator routes on it
- **`tools`** → required; list only what the skill's Flow uses
- **`model`** → `inherit` unless there's a reason; a different model for reviewers reduces self-preference
- **`skills`** → the one skill that holds the procedure, preloaded into the agent's context
- **`fence-deny`** or **`fence-allow`** → optional glob list; kit's `fence.py` hook enforces it

## Body

- ≤ 8 non-blank lines, no headings
- Which skill to run, which inputs come from the prompt, what to return

## Fences

- `fence-deny` → builders: lock the files that judge them
- `fence-allow` → everyone else: write only their own outputs; always include `/tmp/*`
- Globs are repo-relative, fnmatch-style: `*` also matches `/`
- Bash is checked for obvious writes only; the orchestrator reverts anything that slips through

## Hooks

- `hooks:` in agent frontmatter never fired for project agents (verified 2026-09-26, Claude Code 2.1.283), and plugin agents ignore it
- Hooks in `.claude/settings.json` or a plugin's `hooks/hooks.json` do fire for subagents and receive `agent_type`
  - A project agent's `agent_type` is its name; a plugin agent's is `<plugin>:<name>`, like `kit:builder`
- So a per-agent check is a settings hook that reads `agent_type`, like kit's builder stop gate
