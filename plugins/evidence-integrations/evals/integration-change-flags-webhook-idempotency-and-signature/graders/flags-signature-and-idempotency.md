---
type: llm
---

Signature verification and idempotency are the obvious points; most answers
get them. The integration-change skill also treats the processor as an
availability and operability boundary, which is what this grader checks.

PASS only if the response, anywhere in the reply (judge substance, not
placement):
- flags webhook signature verification AND replay protection AND idempotency
  of the order-status update under duplicate delivery; and
- raises at least TWO of the following integration-change points:
  (a) detection — how a missing or failing webhook stream is detected and who
      is alerted (an integration with no alert fails silently);
  (b) replay/recovery — a runbook or reconciliation path to replay or
      re-fetch updates that were lost while the receiver was down;
  (c) contract ownership/versioning — the processor owns the payload
      contract, so what happens when they version or change it without
      notice;
  (d) attribution — the audit trail records the processor as the actor that
      changed the order status (what, when, which event), not an anonymous
      system update.

FAIL if signature verification, replay protection, or duplicate-delivery
idempotency is missing, or if fewer than two of (a)–(d) are raised.
