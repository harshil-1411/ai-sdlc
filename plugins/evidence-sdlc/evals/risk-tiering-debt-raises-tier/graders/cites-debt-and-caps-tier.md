---
type: llm
---

The change described (a cosmetic label reword on an internal admin tool, no
data change, no new endpoint) would be Tier 1 — "internal tooling, non-regulated
UI polish" — on its own.

PASS if the response raises this to Tier 2 specifically because of the named
technical debt (the documented workarounds and/or the zero test coverage in
the touched file), states or implies debt raises the tier by one notch rather
than picking an arbitrary tier, and does not escalate all the way to Tier 3.

FAIL if the response stays at Tier 1 despite the named debt, ignores the debt
signals entirely, jumps straight to Tier 3, or gives a tier with no reasoning
tied to the debt in the file.
