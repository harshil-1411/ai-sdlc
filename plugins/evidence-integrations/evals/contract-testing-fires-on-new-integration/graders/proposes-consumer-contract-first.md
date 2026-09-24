---
type: llm
---

PASS if the response recommends consumer contract tests generated from a
recorded request/response contract, run against a stub on every commit, as the
primary defense — with a full end-to-end sandbox suite explicitly relegated to
a small nightly canary rather than the main proof the integration works.

FAIL if the response's main recommendation is running tests against Stripe's
real sandbox as the primary/only way to catch breakage, or it never mentions a
stub generated from a recorded contract.
