---
type: llm
focus: { source: file, path: '.evidence/test-cases/FIX-221-tenant-isolation.md' }
---

PASS if the authored case(s): have a title describing the behaviour under
test (e.g. "a user cannot open a record belonging to another tenant") rather
than just a feature name, have explicit preconditions and one action per
step, have a specific/observable expected result (not "no error"), carry the
supplied tracker key `FIX-221` in the traceability field/mention and
reference REQ-AUTH-09 in the body, and set priority from the Tier 3 risk tier
rather than an arbitrary guess.

FAIL if the case has no explicit steps/expected results, has a vague expected
result like "no error" or "works correctly", or omits the tracker key /
requirement reference entirely. Since the prompt supplies FIX-221 directly,
a placeholder like `FIX-<TBD>` is a FAIL here — that discipline is correct
only when the key is genuinely missing, and this case gives it one.
