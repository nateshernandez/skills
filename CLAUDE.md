# kit

A Claude Code plugin: skills in `skills/`, agents in `agents/`, hooks in `hooks/hooks.json`, and the Python they run in `scripts/`.

- **Layout** → each skill is `skills/<name>/SKILL.md` plus optional `references/` and `assets/`; skills for working on this repo, never shipped, live in `.claude/skills/`; every script lives in `scripts/` and is run as `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py`
- **Config** → scripts read the user's `.claude/kit/config.json` through `scripts/kit_config.py`; `docs/configuration.md` documents every field and must change with it
- **Hooks stay out of the way** → every hook exits 0 in a project without `.claude/kit/config.json`
- **Skill format** → `skills/write-skill/references/format.md`; agent format → `skills/write-agent/references/format.md`
- **Python** → stdlib only, Python 3.11+; `.claude/rules/python-*.md` cover style
- **TypeScript** → only assets kit copies into projects, like `skills/setup/assets/ux-checks.ts`; Biome formats and lints, `tsc` checks types; `.claude/rules/typescript-*.md` cover style
- **Trying a change** → `claude --plugin-dir .` from a test project loads this checkout instead of the installed plugin
- **Commits** → `.claude/rules/git-commits.md`; pull requests land on `main` by rebase only, so history stays linear
- **Releasing** → the repo's `write-changelog-entry` skill bumps `version` in `.claude-plugin/plugin.json` and writes the `CHANGELOG.md` section; users get nothing new until the version changes

## Checks

CI runs these on every pull request; run them before pushing:

```bash
ruff check scripts && ruff format --check scripts
npm ci && npm run check
uv tool run pyright scripts
python3 scripts/lint_skill.py skills/*/SKILL.md .claude/skills/*/SKILL.md
python3 scripts/check_routes.py skills .claude/skills
python3 scripts/lint_agent.py agents/*.md
claude plugin validate .
```
