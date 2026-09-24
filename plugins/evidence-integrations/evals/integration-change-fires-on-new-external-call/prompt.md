---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
tags: [trigger, integration-change]
---

We want to call a new e-sign provider's API to send contracts out for
signature, and receive a webhook from them when a document is signed. What do
we need to think through before building this?
