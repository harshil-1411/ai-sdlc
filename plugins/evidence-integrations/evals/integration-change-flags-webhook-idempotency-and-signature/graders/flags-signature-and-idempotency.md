---
type: llm
---

PASS if the response specifically asks about or flags: webhook signature
verification (proving the POST really came from the payment processor),
replay protection, and idempotency of the order-status update if the same
webhook is delivered more than once (a state-changing operation must not
double-execute).

FAIL if the response designs the webhook receiver without raising signature
verification or without raising the double-delivery/idempotency risk on the
order-status update.
