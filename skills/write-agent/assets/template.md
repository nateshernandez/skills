---
name: <kebab-case, matches the file name>
description: >
  Use when: <the task situation that should route here>.
  Not when: <the nearest neighbor>.
tools: <Read, Grep, Glob, Bash, ...>
model: inherit
skills:
  - <the skill that holds the procedure>
fence-allow:
  - "<glob this agent may write>"
  - "/tmp/*"
---

Run the <skill> skill for the <inputs> in your prompt.
Return: <the one or two lines the caller needs>.
