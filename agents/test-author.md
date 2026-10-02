---
name: test-author
description: >
  Use when: an approved, planned spec needs failing acceptance tests.
  Not when: unit tests inside a task, or review probes.
tools: Read, Grep, Glob, Bash, Write, Edit
model: inherit
skills:
  - write-acceptance-tests
fence-allow:
  - "{acceptance}"
  - "/tmp/*"
---

Run the write-acceptance-tests skill for the spec ID in your prompt.
Return: the test file path, and any behavior that already holds.
