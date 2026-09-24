---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
tags: [trigger, contract-testing]
---

We're adding a new integration with Stripe for payment processing. How should
we test it so a breakage shows up in our pipeline instead of in production?
