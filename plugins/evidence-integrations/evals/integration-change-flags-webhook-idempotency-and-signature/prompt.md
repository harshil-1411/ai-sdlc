---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
tags: [behavior, integration-change]
---

Design: we're adding a webhook receiver for our new payment processor. It'll
POST transaction updates to us, and on each one we'll update the matching
order's status directly.
