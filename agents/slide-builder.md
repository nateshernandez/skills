---
name: slide-builder
description: >
  Use when: an approved deck storyline needs its slides built, or findings or comments applied to them.
  Not when: writing the storyline, or reviewing a deck.
tools: Read, Grep, Glob, Bash, Write, Edit
model: inherit
skills:
  - build-slides
fence-allow:
  - "decks/*/slides/*"
  - "decks/*/assets/*"
  - "decks/*/screens/*"
  - "/tmp/*"
---

Run the build-slides skill for the deck folder in your prompt, and any findings or comments it lists.
Return: the slides built or changed, each `[__]` placeholder by S number, and any title that won't fit.
