---
type: llm
---

PASS if the response derives the evidence package from the fixture artifact
chain (intent.md, spec.md's requirement IDs, plan.md's test rows) — pointing at
REQ-AUTH-01 and REQ-AUTH-02, naming the covering tests from plan.md, and
stating a re-verification call — rather than writing a generic report from
scratch. It should also state a change-impact assessment (in/out of regulatory
scope) and flag REQ-AUTH-02 (no covering test in the fixture plan) as
`NO COVERAGE`, not soften or omit it.

FAIL if the response writes a generic-sounding evidence report unconnected to
the fixture's actual requirement IDs and test rows, invents a covering test
for REQ-AUTH-02, or omits the missing-coverage finding.
