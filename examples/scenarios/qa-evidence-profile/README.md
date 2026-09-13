# Scenario: proving a regulated-record case, not just naming it

**Who this is for:** a QA lead who has heard this framework's evidence rules stated
abstractly — "evidence is a pointer, never a description" — and wants to see what
actually lands on disk for one real, regulated case. Read this after
[the regulated-change scenario](../regulated-change-tier3/README.md), which builds
the signature capability this scenario later has to change safely.

## The story

> "As a QA reviewer, I want to re-open a review I previously rejected, so the
> reviewer can correct it — but the system must show the prior rejection was
> superseded, not erased."

`signed_documents` is the same regulated record type
[the regulated-change scenario](../regulated-change-tier3/README.md) added
signing to. `.evidence/context/compliance.md` already carries
`evidence_profile: L1, raised to L2 for Tier 2+ and L3 for Tier 3` — set once,
read by `evidence-package`, `test-strategy` and `testrail-authoring` alike, so
none of them re-decide it per change.

## Walkthrough

**1 · Plan.** `intent-capture` writes `intent.md` for **REQ-SIG-03**: a rejected
review can be re-opened; the record must show the rejection was superseded, never
erased. `risk-tiering` marks this **Tier 3** without debate — it touches a signed
record's history, which puts the evidence profile at **L3** for this change:
video for the critical workflow, signed attestation on the manual result.

**2 · Design.** `spec-and-design` writes `spec.md`. Its regulatory control table
checks `21-cfr-part-11.md`'s P11-03 (record protection — nothing about the prior
rejection may be altered) and P11-05 (audit trail — both the rejection and its
supersession must appear, in order, neither obscured).

**3 · Build — `test-designer` derives the case set.** This is the part that used
to be one generic list; it isn't anymore. Reading `test-strategy`'s layer table,
`test-designer` weights its categories per layer and produces:

| Case ID | Category | Layer | What it proves |
| --- | --- | --- | --- |
| SIG-03-F01 | Happy path | Integration | Owner re-opens a rejected review; new state is `reopened`, prior rejection intact |
| SIG-03-N01 | Negative — wrong role | Integration | A non-owner reviewer's re-open attempt is denied server-side, per role and tenant |
| SIG-03-N02 | Negative — wrong state | Integration | Re-opening an already-**signed** (not merely rejected) record is refused |
| SIG-03-W01 | White-box — state transition | Unit | `rejected → reopened` is a legal transition; `signed → reopened` is not — both asserted directly against the state machine, not just the API's response |
| SIG-03-B01 | Boundary / equivalence | Integration | One representative case per input class (valid: `rejected`; invalid: `signed`, `draft`, `archived`) at the state-check boundary, not a guess at where the edge is |
| SIG-03-S01 | Security — tenant isolation | Security | The re-open endpoint is tenant-scoped; cross-tenant record IDs are rejected |
| SIG-03-A01 | Regulated-record — audit trail | Integration | The audit trail shows both the original rejection and the supersession event, in order, neither rewritten |
| SIG-03-M01 | Manual — regulated walkthrough | Manual (L3) | A QA reviewer performs the full reopen-and-resign flow end to end; human attestation is itself part of the evidence |

Six of these are exactly what a generic happy/negative/boundary list would have
produced before this batch of work. `SIG-03-W01` and the equivalence-partition
structure behind `SIG-03-B01` are not — they exist because `test-designer` now
asks, explicitly, whether a state machine is involved before falling back to a
one-size-fits-all case list.

**4 · Test — where each case's evidence actually lands.** This is the part the
framework used to leave undefined:

- `SIG-03-F01` through `SIG-03-A01` (six automated cases): each run's evidence is
  its CI test report, tagged with the tracker key and case ID — L0 is sufficient
  here, nobody signs a unit test.
- `SIG-03-M01` (the manual case), at **L3**: the tester's name, a timestamp, and
  a video of the full reopen-and-resign flow, plus a per-step screenshot at the
  moment of re-signing showing the record identifier, the timestamp, the
  logged-in reviewer, and an environment banner reading "TEST" — never a
  production screenshot standing in for a test one. Filed at
  `validation/evidence/TRACE-1/SIG-03-M01/`, named
  `TRACE-1-SIG-03-M01-step-3.png`, cited by that exact path in the
  `evidence_link` column of `validation/traceability.csv` — a path a reviewer
  can open, not a sentence describing what it would show.

**5 · Deploy.** Tier 3's two-reviewer rule applies: the code owner reads the full
diff, a second reviewer examines the regulated portion specifically, and
`compliance-reviewer` runs its controls-plus-validation pass before the PR opens.

**6 · Maintain — the honest gap this scenario exists to name.** Running
`evidence gaps` against a change like this one will, correctly, sometimes report
`SIG-03-A01` or another automated case under the new `UNVERIFIED-RESULT` category
if the test is structurally tagged to the requirement but no
`validation/traceability.csv` row has ever recorded a pass/fail for it — a
narrower, more honest claim than `NO COVERAGE`: the tag exists next to a real
test declaration, but nobody has recorded whether that test was ever actually
run. This repository's own `cli/README.md` worked example shows this exact class
of gap against its own history. It is not a defect in the case design above; it
is why `test-strategy`'s "Evidence produced" column and the attestation rules in
`testrail-authoring` exist — a structural tag proves a case was *designed*, never
that it was *proven*, and the evidence profile in force is what closes that gap
for the cases that matter enough to need closing.

## What made this different from the regulated-change scenario

That scenario built the signing capability. This one changes behaviour *around*
an already-signed record without ever touching the signature itself — and stays
Tier 3 anyway, because the rule is "touches a signed record's history," not
"touches the signature bytes." The evidence-profile mechanism, not the tier
table, is what decided the manual case needed video and attestation rather than
just a screenshot: a Tier 3 label alone does not say *how much* evidence a given
case needs, only that the ceiling is high.

## Read next

- [`test-strategy`](../../../plugins/evidence-quality/skills/test-strategy/SKILL.md) —
  the "Evidence produced" and "Coverage is interpreted, not generated" sections
- [`test-designer`](../../../plugins/evidence-quality/agents/test-designer.md) —
  the white-box/equivalence-partitioning categories this scenario's case table uses
- [`evidence-package`](../../../plugins/evidence-compliance/skills/evidence-package/SKILL.md) —
  "Step 0 — read or set the evidence profile," the L0-L3 table and screenshot
  requirements this scenario's Step 4 follows
- [`testrail-authoring`](../../../plugins/evidence-quality/skills/testrail-authoring/SKILL.md) —
  "Regulated attestation," for what `SIG-03-M01`'s record must contain beyond pass/fail
- [`cli/README.md`](../../../cli/README.md) — the `UNVERIFIED-RESULT` gap category
- [Scenario: a regulated change](../regulated-change-tier3/README.md) — the
  signature capability this scenario changes the behaviour around
