---
type: llm
---

Most advice here stops at "sandbox suites are flaky, add contract tests". The
contract-testing skill is more specific, and this grader checks the specific
parts.

PASS only if the response, anywhere in the reply (judge substance, not
placement):
- keeps a real-sandbox job only as a small canary/smoke test whose purpose is
  proving the credential still works and the endpoint still exists (not
  "exercise every code path"), and moves coverage to consumer contract tests
  that run on every commit against a stub;
- says that stub is generated from a recorded contract (recorded requests and
  responses, or the partner's published spec) rather than hand-written from
  the partner's documentation — or states in substance that hand-written stubs
  encode our beliefs and so agree with our code even when both are wrong;
- names explicit failure-path coverage — at least three of: timeout, HTTP 500,
  HTTP 429 / rate limit, malformed body, a response that is valid but
  semantically wrong — OR an explicit idempotency test (send the same request
  twice and assert the effect happened once).

FAIL if the response endorses the 200-call sandbox suite as adequate, or
recommends contract tests/mocks without saying the stub must come from a
recorded contract rather than hand-written docs, or names neither the
failure-path set nor an idempotency test.
