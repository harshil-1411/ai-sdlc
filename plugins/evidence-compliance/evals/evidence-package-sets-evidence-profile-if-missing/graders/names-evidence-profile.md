---
type: llm
---

PASS if, since `.evidence/context/compliance.md` has no `evidence_profile` set
in the fixture, the response explicitly names an evidence profile level (L0-L3)
for this Tier 3 change — L3, since it involves a signature-free but
audit-trail-bearing authentication workflow at Tier 3 — states it should be
recorded in the compliance profile, and does not silently proceed as if a
profile already existed.

FAIL if the response never mentions an evidence profile level at all, or
proceeds to assemble the package without ever surfacing that this decision
was missing and needed to be made.
