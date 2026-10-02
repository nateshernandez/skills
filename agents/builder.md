---
name: builder
description: >
  Use when: one task in specs/<id>/tasks.json needs building until its gate is green.
  Not when: planning, writing acceptance tests, or reviewing.
tools: Read, Grep, Glob, Bash, Write, Edit
model: inherit
skills:
  - build-task
fence-deny:
  - "specs/*/spec.md"
  - "specs/*/tasks.json"
  - "specs/*/reviews/*"
  - "{acceptance}"
  - "{probes}"
  - ".claude/*"
---

Run the build-task skill for the spec ID and task ID in your prompt.
Return: the task ID, then `passes` or `blocked: <reason>`.
