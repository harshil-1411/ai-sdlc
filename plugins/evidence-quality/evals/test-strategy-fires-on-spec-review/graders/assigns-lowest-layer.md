---
type: llm
---

Choosing the lowest sensible layer is generic good practice. The
test-strategy skill also fixes the output shape and the regulated-change
cases; this grader checks those.

PASS only if the response, anywhere in the reply (judge substance, not
placement):
- assigns each requirement to the lowest layer that can prove it (REQ-AUTH-02's
  audit event at integration/API level, not only via end-to-end UI);
- gives, per requirement, a row or entry naming the layer, whether it is
  automated, a test case ID (a placeholder such as `TC-TBD` is acceptable),
  the automated test name, and the **evidence produced** as a concrete
  artifact pointer (a test report, run ID, JUnit XML path, screenshot path) —
  not a description of what the evidence would show;
- for the audit-trail requirement, asserts the audit event's specific fields
  (e.g. actor, tenant, timestamp, event type) and/or ordering, not merely
  "an audit event exists"; and
- does not propose gating either requirement on an aggregate code-coverage
  percentage.

FAIL if every requirement is pushed to end-to-end/manual without
justification, if there is no per-requirement row naming an evidence
artifact, if the audit test only checks that "something was logged", or if a
coverage-percentage gate is proposed.
