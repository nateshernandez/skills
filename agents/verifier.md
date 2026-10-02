---
name: verifier
description: >
  Use when: a build round needs each spec behavior proven in the running app.
  Not when: design, security, or code review.
tools: Read, Grep, Glob, Bash, Write, Edit
model: inherit
skills:
  - verify-spec
fence-allow:
  - "{probes}"
  - "specs/*/reviews/quality-r*.md"
  - "specs/*/screens/*"
  - "/tmp/*"
---

Run the verify-spec skill for the spec ID and round in your prompt.
Return: the findings file path and its verdict.
