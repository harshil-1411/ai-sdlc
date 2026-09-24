---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
tags: [behavior, schema-migration]
---

Just add the new `orders.currency_code` column and drop the old
`orders.legacy_currency` column in the same migration — we want this done in
one deploy, no need to phase it.
