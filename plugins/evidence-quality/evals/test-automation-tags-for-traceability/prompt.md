---
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill, Write]
---

Write an automated integration test for the new export-throttling feature we
just built (tracker key FIX-220), automating manual case TC-118. Add it to
`tests/export/throttle.test.ts`, next to the existing test there.
