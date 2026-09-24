---
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
tags: [non-trigger, agent-trust-boundaries]
---

Can you refactor our nightly batch job that reads rows from our own internal
`orders` table and recomputes a summary total? It only ever reads data we
wrote ourselves, no external input.
