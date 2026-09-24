---
type: llm
---

PASS if the response reads like the org's spec.md template filled in from the
fixture intent: it states a risk tier, gives requirements traceable back to the
intent, addresses regulatory control impact (even if "not applicable" per the
compliance profile), and lists an "Areas of concern" section rather than
omitting it.

FAIL if it invents a technology, datastore, or component not present in the
fixture stack profile, skips the risk tier, or skips areas of concern entirely
with no comment.
