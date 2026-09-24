---
type: llm
---

Generic advice covers trust, availability and "think about compliance". The
integration-change skill requires specific things beyond that; this grader
checks them.

PASS only if the response, anywhere in the reply (judge substance, not
placement or headings), includes all three of:
1. **Audit entry for the crossing.** It says the audit trail must record the
   document leaving the platform with at least three of: what left, when, to
   whom (the provider), and under whose authority — and/or that the external
   provider must be recorded as an attributable actor when its webhook changes
   a record's state. A bare "log the API call" does not count.
2. **Data at the boundary.** It asks to enumerate exactly which fields cross
   in each direction, AND raises at least one of: retention/deletion of the
   documents on the provider's side, or data residency of the provider.
3. **Deliverable.** It says the answers belong in the spec (an integration
   section in spec.md or equivalent design record) and/or a runbook entry
   covering how to tell the integration is broken, how to degrade or fail
   over, who to contact at the provider, and how to replay anything lost —
   at least two of those four runbook items must be named.

It must also raise webhook signature verification and idempotency/retry of
the outbound send somewhere in the reply.

FAIL if any of the three numbered items is missing, or if the response only
discusses authentication/authorization and generic reliability.
