---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
tags: [trigger, schema-migration]
---

We need to rename the `users.full_name` column to `users.display_name` and
have the app read from the new name. Can you write the migration?
