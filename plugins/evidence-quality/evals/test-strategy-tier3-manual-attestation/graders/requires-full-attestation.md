---
type: llm
---

PASS only if the response, anywhere in the reply (judge substance only, not
placement — the elements count wherever they appear, including under a
separate heading after an initial row or table):
- says a bare PASS/FAIL status is not sufficient for this Tier 3 manual
  result: the record must carry the tester's name, a timestamp, and the
  execution method (e.g. a screenshot or video reference);
- gives the test plan row a manual test case ID (a placeholder such as
  `TC-TBD` is acceptable) and names the evidence produced as a concrete
  artifact pointer (a run record, signed record, screenshot/video path) —
  per test-strategy, a manual row with no test case ID is an incomplete plan;
- because this is a signature/approval change, includes a check of what is
  displayed with the signature (e.g. signer name, date/time, meaning of the
  signature) AND of how the approval is bound to the specific record (it
  cannot be detached, copied to another record, or survive the record being
  altered); and
- does not suggest automating the walkthrough to replace the human execution
  the protocol calls for.

FAIL if the response accepts a plain pass/fail, omits any of tester name /
timestamp / execution method, gives no test case ID for the manual row,
omits either the signature-display check or the record-binding check, or
suggests automating the walkthrough to replace required human execution.
