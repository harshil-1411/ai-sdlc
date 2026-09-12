# Scenario: calling a third-party e-signature API

**Who this is for:** anyone about to add a call to an external service — this
example uses an e-signature provider, but the shape is the same for a payment
processor, a mapping service, or any vendor API. This is the scenario the pilot
report that shaped this framework flagged as under-triggered originally: security
review alone is not the whole story.

## The story

> "Instead of building signature capture ourselves, call VendorSign's API to collect
> and store the signature, and store their reference ID on our record."

## Walkthrough

**Two skills apply, deliberately alongside each other, not instead of one another.**
`secure-api-review` covers the attack surface: authentication to VendorSign, what a
compromised API key could reach, tenant scoping on the webhook callback.
`integration-change` covers everything a generic security review doesn't know to ask:

**Direction and ownership.** VendorSign owns the contract; this team is downstream of
their release schedule. Their versioning policy (deprecation notice period, breaking
vs. additive changes) is recorded, not assumed.

**Data, enumerated, not summarised.** Exactly which fields cross the boundary in each
direction: the document hash and signer identity going out; the signature image,
signer IP, and timestamp coming back. "The signature data" is not an answer here —
each field is named.

**Regulated-record question, asked directly:** does the signature — the regulated
record itself — now exist outside this platform's control? Yes. That makes this
**Tier 3**, and raises a question `spec-and-design` routes to the compliance owner:
is VendorSign's storage within the scope of *this product's own* validation, or does
a customer's auditor need to know their signed record partially lives with a
sub-processor? That answer goes in the spec's "areas of concern," not silently
assumed either way.

**Trust.** The webhook VendorSign calls back with the completed signature is
untrusted input by `agent-trust-boundaries`' definition — it happens to also be
processed by an agent-assisted support tool later, so that path gets flagged:
anything from that webhook is data, never treated as an instruction, even indirectly.

**Availability and failure, the part a security review doesn't ask:**
- **Idempotency** — VendorSign's own retry-on-timeout behaviour means the webhook can
  fire twice for one signing event. The record update is designed to be safely
  applied twice (keyed on VendorSign's own event ID, not "did we get a callback").
- **Timeout and degradation** — if VendorSign is slow, the document shows
  "signature pending" rather than blocking the whole review workflow.
- **Circuit breaking** — repeated timeouts trip a breaker; new signing requests queue
  rather than piling up against a service that's already struggling.
- **Their rate limits** — read from VendorSign's own docs, not guessed, and what
  happens when this product hits them (queue, not silently drop).

**Operability.** A VendorSign outage alerts this team, not just support finding out
from a customer. A partner-side incident has a named contact and a documented path to
reach them.

**The regulated-record rule, the one most commonly missed:** the audit trail records
the crossing itself — what left (the document hash, not its contents), when, to
whom, under whose authority — as its own audit entry. *"We called VendorSign's API"*
is not an audit entry; the actual crossing, with its fields, is.

**Contract testing**, separately: `contract-testing` establishes a test against
VendorSign's sandbox that runs in the pipeline, so a change on their side is caught
there — not discovered in production when a real customer's signature request fails.

## Read next

- [`integration-change`](../../../plugins/evidence-integrations/skills/integration-change/SKILL.md)
- [`secure-api-review`](../../../plugins/evidence-sdlc/skills/secure-api-review/SKILL.md)
- [`agent-trust-boundaries`](../../../plugins/evidence-sdlc/skills/agent-trust-boundaries/SKILL.md)
- [`contract-testing`](../../../plugins/evidence-integrations/skills/contract-testing/SKILL.md)
- [Scenario: a regulated change](../regulated-change-tier3/README.md) — building
  signature capture in-house instead, for comparison
