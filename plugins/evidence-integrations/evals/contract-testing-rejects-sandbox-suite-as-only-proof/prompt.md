---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
tags: [behavior, contract-testing]
---

Our team just set up a nightly job that makes about 200 real API calls against
the shipping partner's sandbox to exercise every code path — that's our whole
integration test suite for that partner. Any concerns with that approach?
