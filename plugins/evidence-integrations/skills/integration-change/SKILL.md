---
name: integration-change
description: Design, review and change any integration between the platform and an external system — inbound APIs, outbound calls, webhooks, file transfers, identity federation, partner platforms, connectors. Use whenever an integration is added, versioned, deprecated or debugged, whenever a partner announces a change, and whenever a spec proposes calling or being called by anything outside the platform. Treat every integration as a trust, availability and compliance boundary at once.
---

# Integration change

An integration is three boundaries at once: a **trust** boundary (someone else's data
and instructions), an **availability** boundary (their outage becomes your incident),
and for the organisation a **compliance** boundary (regulated records may leave the platform).
Most integration incidents come from treating it as only the first.

## The questions every integration spec must answer

**Direction and ownership**
1. Who calls whom, and who owns the contract? If they own it, you are downstream of
   their release schedule — say so.
2. What is the versioning story, and what happens when they version without telling you?

**Data**
3. Exactly which fields cross the boundary, in each direction. Enumerate them; "the
   the record data" is not an answer.
4. Does any regulated record or sensitive data class cross? If yes, this is
   Tier 3 and needs the full regulatory treatment — including whether the receiving
   system is within the customer's validated scope.
5. Does data cross a residency boundary? Check the deployment profile for what is
   permitted.
6. What is retained on their side, for how long, and can it be deleted on request?

**Trust**
7. Inbound payloads are untrusted input. Apply the `agent-trust-boundaries` skill —
   especially if any payload reaches a model.
8. Authentication in both directions: mechanism, credential rotation, and what a
   compromised credential could reach.
9. Webhook authenticity: signature verification, replay protection, idempotency keys.

**Availability and failure**
10. What happens when they are slow? Timeouts, and what the user sees.
11. What happens when they are down? Queue, degrade, or fail — decide explicitly.
12. Retry policy, backoff, and **idempotency** — a retried state-changing
    operation must not double-execute.
13. Circuit breaking, and what trips it.
14. Their rate limits, and what happens when you hit them.

**Operability**
15. How is a failure detected, and by whom? An integration with no alert is an
    integration that fails silently until a customer calls.
16. What is in the audit trail when an integration acts on a regulated record? The
    external system is an actor and must be attributable.
17. How is a partner-side incident communicated to your support function?

## Regulated-record rule

If a regulated record crosses the boundary, the audit trail must record the crossing:
what left, when, to whom, under whose authority. "We called their API" is not an audit
entry. This is the single most commonly missed control in integration work.

## Deprecating an integration

Deprecation is a change with its own spec, its own customer communication, and its own
validation impact — customers may have validated workflows that depend on it. Never
treat removal as smaller than addition.

## Output

Integration changes get their own section in `spec.md` answering all of the above, plus
a runbook entry covering: how to tell it is broken, how to fail over or degrade, who to
contact on the partner side, and how to replay anything that was lost.
