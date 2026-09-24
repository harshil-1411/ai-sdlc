---
type: llm
---

Moving slow checks later and separating blocking from advisory is standard
advice. The continuous-testing skill adds rules generic answers usually skip;
this grader requires them.

PASS only if the response, anywhere in the reply (judge substance, not
placement):
- moves slower checks (full e2e, extended/DAST security) out of the per-push
  commit stage to PR, deploy-to-test, nightly or pre-release, and separates
  blocking checks from advisory ones; AND
- states that each stage produces evidence (test report, scan report, run
  record, SBOM, etc.) that is posted somewhere durable and reachable from the
  tracker key / change — not just a green check; AND
- includes at least ONE of:
  (a) a ~10-minute budget for the commit stage, guarded/tracked as a metric;
  (b) impact-scoped (affected-tests) runs at the commit stage while keeping a
      full unscoped run at PR/nightly/pre-release — and not scoping Tier 3 /
      regulated changes;
  (c) rollback triggered by post-deploy checks being rehearsed on a schedule
      with the date recorded;
  (d) the pre-release stage closing with a test summary report whose go/no-go
      is signed by a named human.

FAIL if the full suite still runs on every push, if blocking vs advisory is
not distinguished, if per-stage evidence posted durably and linked to the
tracker key is never mentioned, or if none of (a)–(d) appears.
