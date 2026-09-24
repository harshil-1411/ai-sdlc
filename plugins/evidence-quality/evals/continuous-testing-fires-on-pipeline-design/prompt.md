---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
tags: [trigger, continuous-testing]
---

We're redesigning our CI pipeline. Right now everything — unit, integration,
full e2e, security scans — runs on every push and the whole thing takes 25
minutes. What should run where?
