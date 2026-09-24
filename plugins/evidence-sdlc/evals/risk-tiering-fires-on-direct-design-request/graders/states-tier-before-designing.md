---
type: llm
---

PASS if the response commits to a stated risk tier (Tier 1, 2, or 3) with a
reason, prominently and early — as its own clearly labeled statement near the
top of the reply (e.g. a first line, heading, or its own labeled bullet such as
"Tier stated: Tier 2") — for this non-regulated, non-production-critical
"saved search" feature (Tier 1 or Tier 2 is reasonable here). This still
counts as a PASS even if the response cannot produce the schema itself because
of an unrelated missing-stack-profile precondition — what matters is that a
tier decision was actually made and clearly surfaced, not that a schema exists.

FAIL if the response never states a tier, buries the tier only inside a long
paragraph with no clear label, leaves the tier as an open/unresolved question
("this decides whether it's Tier 2 or Tier 3") instead of a committed decision,
states a tier only after fully designing the schema, or classifies it Tier 3
without any regulated-record, auth, or audit-trail justification.
