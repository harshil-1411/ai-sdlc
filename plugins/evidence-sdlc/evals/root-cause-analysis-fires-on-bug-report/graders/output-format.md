---
type: llm
---

PASS if the response distinguishes the trigger (guest checkout specifically,
after yesterday's deploy) from a proposed root cause, lists its assumptions
explicitly, and either states the root cause with evidence or says which
evidence is still missing rather than guessing.

FAIL if the response proposes a fix without ever separating trigger from root
cause, or without listing assumptions, or asserts a root cause with no
supporting evidence from what was given.
