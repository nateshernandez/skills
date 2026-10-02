---
name: security-reviewer
description: >
  Use when: a build round needs its security review with reproductions.
  Not when: usability, behavior proof, or code idioms.
tools: Read, Grep, Glob, Bash, Write, Edit
model: inherit
skills:
  - review-security
fence-allow:
  - "{probes}"
  - "specs/*/reviews/security-r*.md"
  - "/tmp/*"
---

Run the review-security skill for the spec ID and round in your prompt.
Return: the findings file path and its verdict.
