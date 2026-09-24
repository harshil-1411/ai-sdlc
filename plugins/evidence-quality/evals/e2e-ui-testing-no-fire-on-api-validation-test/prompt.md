---
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
tags: [non-trigger, e2e-ui-testing]
---

Write a pytest test asserting that POST /orders rejects a negative quantity with a 422 and a field-level error.
