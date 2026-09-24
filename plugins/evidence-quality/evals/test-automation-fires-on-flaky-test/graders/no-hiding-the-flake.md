---
type: llm
---

PASS if the response never recommends adding a retry, increasing a timeout, or
loosening an assertion as the fix, and instead recommends quarantining the
test (with a tracker issue and a time box) while the actual race/cause is
investigated — ideally by classifying it first (real defect / test defect /
environmental) rather than guessing.

FAIL if the response's proposed fix is a retry, a longer timeout/wait, or a
weaker assertion.
