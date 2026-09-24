---
type: llm
---

PASS if the response treats REQ-AUTH-02's missing test coverage (per the
fixture plan.md, which has no automated test for it) as a blocking release
finding, not a minor note, and does not claim the requirement is verified
because the code looks right.

FAIL if the response says REQ-AUTH-02 is ready to ship, softens the missing
coverage into a non-blocking observation, or claims it is verified without
pointing at a test that actually ran.
