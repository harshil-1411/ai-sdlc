---
type: llm
---

The contract-testing skill has three rules plain advice usually misses here:
(1) a failing contract test means one of exactly three things — our code
changed, their contract changed, or our understanding was wrong — and which
one must be established before anything is edited; updating a contract to make
a test pass is as bad as editing a test to make a fix pass; (2) contracts and
stubs are regenerated from a recorded contract (recorded real traffic or the
partner's published spec/OpenAPI), never hand-edited from what we believe the
partner does; (3) contracts are versioned, and the old version is kept until
the migration completes, so both sides of a partner change can be tested.

PASS only if the response does all of the following, anywhere in the reply
(judge substance, not placement or wording):
- declines to hand-edit/overwrite the contract before the cause is
  established, and names the diagnosis as distinguishing our change vs. the
  partner's contract change vs. a misunderstanding (all three possibilities,
  in substance);
- says that if the partner's contract did change, the new contract should be
  re-recorded / regenerated from the partner's actual response or published
  spec rather than hand-edited;
- says the change should be captured as a new contract version while the old
  one is kept (not overwritten in place) until our code has migrated — or, in
  substance, that the partner's type change is a breaking change our consumer
  code must be updated and tested for, rather than something the contract edit
  alone resolves.

FAIL if the response hand-edits or endorses hand-editing and overwriting the
contract file, or never mentions regenerating/re-recording the contract from
the partner's real response or spec, or treats the one-line edit as the whole
fix without addressing versioning / our consumer code's handling of the new
type.
