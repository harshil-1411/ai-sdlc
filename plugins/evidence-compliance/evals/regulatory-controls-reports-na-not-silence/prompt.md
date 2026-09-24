---
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill]
---

We're adding a small internal cron job that recomputes a nightly usage count
from our own database and writes it to a metrics table nobody else reads. No
customer data leaves the system and there's no user-facing change. Run this
against our applicable controls before we ship it.
