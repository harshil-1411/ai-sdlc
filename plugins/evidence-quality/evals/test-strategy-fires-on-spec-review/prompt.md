---
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill, Agent]
tags: [trigger, test-strategy]
---

Here's the relevant part of our spec for the MFA-recovery feature:

REQ-AUTH-01: Customer can request a recovery link via verified email.
REQ-AUTH-02: The recovery event is written to the audit trail.

What's our test approach for these two requirements?
