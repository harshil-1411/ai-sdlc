---
type: llm
---

PASS if the response flags that a large real-sandbox call suite is slow,
flaky, and dependent on the partner's uptime, and recommends shrinking it to a
small canary/smoke test while moving the real coverage to consumer contract
tests against a generated stub.

FAIL if the response endorses the 200-call real-sandbox suite as adequate
integration testing without raising the flakiness/dependency problem or
proposing consumer contract tests instead.
