---
name: test-strategy
description: Design the test approach for a change — which layer each requirement is proven at, what is automated versus manual, and what evidence each produces. Use this during spec and plan, whenever someone asks how something will be tested, whenever a requirement has no named test, and before any test case or automated test is written. Read the repository profile for the actual test frameworks rather than assuming any.
---

# Test strategy

Read `.evidence/context/stack.md` first for the real test frameworks and commands in
this repository. Do not assume a stack.

## Assign every requirement to a layer

For each `REQ-<area>-<nn>`, decide the **lowest layer that can actually prove it**:

| Layer | Proves | Runs |
| --- | --- | --- |
| Unit | Logic, calculation, validation, state transitions | Every commit |
| Integration / API | Contracts, authorisation, persistence, audit events emitted | Every commit |
| Contract | Agreement with an external integration | Every commit + on partner change |
| End-to-end | User-visible journeys through the real UI | Per PR (smoke) + nightly (full) |
| Manual / exploratory | Judgement, usability, regulated workflow walkthroughs, anything genuinely not automatable | Per release |
| Performance | Load and latency requirements | Scheduled + before release |
| Security | Authz, tenancy, injection, dependency posture | Every commit + scheduled |

Push proof down. A requirement proven end-to-end that could have been proven at the
API layer costs ten times as much to run and is ten times flakier.

## Decide automated vs manual honestly

Automate: anything deterministic and repeated.
Keep manual: judgement, first-time exploratory passes, and regulated workflow
walkthroughs where a human attesting to what they saw is itself part of the evidence.

**Do not automate a regulated walkthrough purely to save time and then present the
automated run as if a human had performed it.** If the validation protocol calls for
human execution, the case stays manual and the run record carries the tester's name.

## Output — the test plan section

Produce a table that goes into `plan.md`:

| REQ ID | Layer | Automated? | Test case ID | Automated test name | Evidence produced |
| --- | --- | --- | --- | --- | --- |

**Any requirement with no row is an incomplete plan.** Any row with `Automated? = no`
and no test case ID is an incomplete plan.

## Regulated changes

For anything touching regulated records, add explicitly:
- a test asserting the audit event fires with the right fields, in the right order
- a test asserting authorisation is enforced server-side, per role and per tenant
- for approval- or signature-related changes, a test asserting what is displayed and
  how the approval is bound to the record

These three are the ones that get missed, and they are the ones that matter.
