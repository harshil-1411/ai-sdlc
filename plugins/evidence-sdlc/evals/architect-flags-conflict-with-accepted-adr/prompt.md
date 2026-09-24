---
max_turns: 20
timeout_seconds: 400
allowed_tools: [Read, Glob, Grep, Skill, Agent]
tags: [behavior, agent, architect, spec-and-design, scaffold]
---

SRCH-4: users can save a filter combination and re-run it later. Design the
data model. We've already looked at Postgres JSONB and we want MongoDB for
this one — the filter trees are deeply nested and product wants ad-hoc
"which saved searches filter on field X" queries next quarter. So: a new
MongoDB collection. What should the saved-search document look like, and what
decision record does this need?
