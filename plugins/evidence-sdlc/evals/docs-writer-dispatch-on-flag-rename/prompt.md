---
max_turns: 20
timeout_seconds: 400
allowed_tools: [Read, Glob, Grep, Skill, Agent, Edit, Write]
tags: [behavior, agent, docs-writer, scaffold, needs-write]
---

CLI-22 just merged: the `--timeout` flag (seconds) is now `--timeout-ms`
(milliseconds, default 30000) — see src/cli/options.ts and the spec in
intent/2026-09-18-timeout-ms/. The code is done; please get the documentation
in line with it.
