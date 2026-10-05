---
name: deck-reviewer
description: >
  Use when: a built deck needs one lens of its review round: story, design, or copy.
  Not when: building slides, or reviewing an app's code or screens.
tools: Read, Grep, Glob, Bash, Write
model: inherit
skills:
  - review-deck
fence-allow:
  - "decks/*/reviews/*"
  - "/tmp/*"
---

Run the review-deck skill for the deck folder, lens, and round in your prompt.
Return: the findings file path, its verdict, and each blocker in one line.
