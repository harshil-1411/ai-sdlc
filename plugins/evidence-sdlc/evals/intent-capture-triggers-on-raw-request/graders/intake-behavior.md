---
type: llm
---

PASS if the response behaves like an intake interview for a new intent: it asks
about, or explicitly marks as unknown, at least two of (who is affected, whether
a regulated record is involved, what "better" looks like in a measurable way,
what is out of scope) — or it drafts an intent.md-shaped summary covering those
points.

FAIL if the response jumps straight to a technical solution (an API design, a
database change, specific code) without first establishing the problem
statement, or if it ignores the request.
