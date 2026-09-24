---
type: llm
---

The continuous-testing skill draws a precise block/inform line: contract-test
failure BLOCKS; agent/bot review findings and non-critical findings INFORM
the human reviewer (attached to the PR) and never gate automatically — "a
findings count that gates a merge automatically will be gamed within a
month; human approval, informed by findings, is the control"; and a merge is
never gated on an aggregate coverage percentage (a drop in coverage of a
regulated path may block, but not a repository-wide number).

PASS only if the response, anywhere in the reply (judge substance, not
placement):
- rejects rule (1): bot findings should attach to the PR to inform the human
  reviewer rather than a findings count automatically blocking (it may keep
  critical/high security findings as blocking);
- rejects rule (2) as an aggregate coverage-percentage gate (it may propose
  blocking on coverage of a regulated/critical path dropping, or reporting
  diff coverage to the reviewer, instead);
- rejects rule (3): contract-test failures should keep blocking, and the
  noise should be fixed (flake triage, re-recorded contracts, quarantine with
  an owner) rather than downgrading the check to advisory.

FAIL if the response endorses any of the three rules as proposed, or leaves
any of them unaddressed.
