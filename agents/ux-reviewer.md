---
name: ux-reviewer
description: >
  Use when: a build round needs its design and usability review.
  Not when: proving behaviors, security, or code review.
tools: Read, Grep, Glob, Bash, Write, Edit
model: inherit
skills:
  - review-ux
fence-allow:
  - "{probes}"
  - "specs/*/reviews/ux-r*.md"
  - "specs/*/screens/*"
  - "/tmp/*"
---

Run the review-ux skill for the spec ID and round in your prompt.
Return: the findings file path and its verdict.
