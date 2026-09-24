---
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill]
---

We're about to change how the `sessions` table stores the authenticated
user's role and how access is authorised for the new `/api/admin/*` routes.
Can you review this against the controls that apply to us before we merge?
