# Changelog

What each release of kit changes for the people using it. Newest first.

## 0.1.0 (2026-10-02)

- **Added** the build pipeline: `/kit:build` takes a request through spec, plan, failing tests, task-by-task build, four-lens review, and a report
- **Added** `/kit:setup`: detects the stack, writes `.claude/kit/config.json` from a Playwright, Vitest, or Jest preset, and checks the gate is green
- **Added** gates: `mark_task.py` marks a task done only when `check` and the spec's tests pass, skipping behaviors later tasks will build
- **Added** hooks: write fences per agent, format and lint on every write, and a stop gate that keeps a builder working while its gate is red
- **Added** authoring skills for decision records, rules, skills, agents, and a `.claude/` changelog, each with its own lint
- **Added** a commit rule that setup installs: short imperative subjects, one commit per change, branches rebased onto `main`
