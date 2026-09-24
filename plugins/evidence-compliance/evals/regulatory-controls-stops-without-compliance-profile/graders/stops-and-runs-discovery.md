---
type: llm
---

PASS if the response states that `.evidence/context/compliance.md` does not
exist, declines to guess which regulatory framework applies, and says
`compliance-discovery` needs to run first — without producing a per-control
verdict table for an invented or assumed framework.

FAIL if the response proceeds to apply a specific framework (SOC 2, HIPAA,
GDPR, or any other) that it did not confirm from a compliance profile, or
produces a control verdict table despite the missing profile.
