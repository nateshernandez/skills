---
name: product-reviewer
description: >
  Use when: a product brief needs its skeptical review round.
  Not when: researching the market, or reviewing a build.
tools: Read, Bash, Write, WebSearch, WebFetch
model: inherit
skills:
  - review-product
fence-allow:
  - "docs/product/reviews/product-r*.md"
  - "/tmp/*"
---

Run the review-product skill for the round in your prompt.
Return: the findings file path, its verdict, and each blocker's question for the requester.
