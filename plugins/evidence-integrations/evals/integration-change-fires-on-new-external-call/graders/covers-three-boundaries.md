---
type: llm
---

PASS if the response frames this integration as more than a security surface —
it raises at least one concern from each of: trust (webhook payload is
untrusted input, signature verification), availability (what happens when the
provider is slow/down, retries, idempotency of a retried signature-request
call), and compliance (whether a signed document is a regulated record, and
whether the audit trail records what left the platform, when, to whom).

FAIL if the response only discusses authentication/authorization (a generic
security review) and never raises availability/retry/idempotency or the
regulated-record/audit-trail question for the outbound document.
