---
name: testrail-authoring
description: Author manual test cases into the team's test management system in its required format, carrying the traceability identifier, and link them back to the tracker issue. Use this whenever manual test cases are needed for a change, whenever someone asks for test cases to be written or updated, when a regression suite needs extending, and when a release test run is being prepared. Read the tool's field requirements from the profile before writing anything.
---

# Authoring manual test cases

Read `.evidence/context/toolchain.md` for how this session reaches the test management
system and whether it may **write** to it. If the write decision is not recorded there,
produce the cases as a reviewable file and stop — do not write into a system of record
on an assumption.

## Before writing a single case

Test management tools reject writes that do not match the project's template and
required custom fields, and the failure is opaque. Establish first:

- The project and suite the cases belong in, and the section hierarchy
- The **template** in use, because template choice changes which fields are valid
- The required custom fields and their allowed values
- The field that carries the tracker key
- The field that carries automation status, if the tool tracks it

Record these in the repository profile once, so future sessions do not rediscover them.
If the tool exposes a "list case fields" capability, call it at the start of the session
rather than guessing field names.

## Writing the case

Each case:
- **Title** — the behaviour being verified, not the feature name. "A user cannot open a record
  belonging to another tenant" beats "Tenant isolation".
- **Preconditions** — state, data, roles, environment. Explicit enough that two testers
  produce the same run.
- **Steps** — one action per step, with the expected result for that step. A step whose
  expected result is "no error" is not a test.
- **Expected result** — observable and specific. Where a regulated record is involved,
  the expected result must name the audit entry, the timestamp behaviour, and what is
  displayed to the user where an approval or signature is involved.
- **Traceability** — the tracker key in its designated field, and the `REQ-<area>-<nn>`
  it proves in the case body. **If the requester already gave you the tracker key in
  their request, use that key — do not leave the field `TBD` or a placeholder while
  waiting on a connector to confirm something you already have.** For example, if the
  request says "tracker key FIX-221", `custom_tracker_key` is `FIX-221`, full stop —
  a placeholder in that situation is not caution, it is discarding a fact you were
  handed. Treat the key as genuinely missing, and placeholder it, only when no one has
  stated it anywhere in the conversation and no connector can supply it.
- **Priority** — from the risk tier of the change, not from enthusiasm.

## Write the link back

After creating cases, record the case IDs on the tracker issue. A case that references
the issue while the issue does not reference the case is a half-chain, and half-chains
are what make audits expensive.

## Regression suite hygiene

- Every defect that escaped to production earns a permanent regression case.
- When a requirement is retired, retire its cases — do not leave them running forever.
  Record the retirement; deleting evidence of what used to be tested is its own problem.
- Cases that have never failed in two years and cover code that never changes are
  candidates for automation or retirement, not for silent perpetuity.

## Regulated attestation

For a Tier 3 manual result, the case record is not complete with a pass/fail alone.
It must carry the tester's name, a timestamp, and the execution method (screenshot
or video reference) — see `test-strategy`'s "Regulated changes" section for why this
content, not just a status, is what the attestation is. Recording only "PASS" for a
Tier 3 case is the same failure as marking a case passed without executing it: a
status with no attestation behind it.

## Never

Never mark a case as passed. You author and organise cases; execution and results are a
human or a pipeline act, and the record must show which.
