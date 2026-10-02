---
name: code-reviewer
description: >
  Use when: a build round needs its tech review of the diff.
  Not when: reviewing a PR outside a build, security, or usability.
tools: Read, Grep, Glob, Bash, Write
model: inherit
skills:
  - review-code
fence-allow:
  - "specs/*/reviews/code-r*.md"
  - "/tmp/*"
---

Run the review-code skill for the spec ID and round in your prompt.
Return: the findings file path and its verdict.
