---
name: evidence-package
description: Derive the compliance evidence a project owes — traceability matrix, change-impact assessment, validation or qualification records, audit evidence packs — from the committed artifact chain instead of assembling it by hand. Use when a change is merged, when a validation or evidence package is assembled for a release or audit, when someone mentions traceability, revalidation or evidence for a customer, and whenever a control is claimed without a pointer behind it.
---

# Evidence package

Compliance evidence is usually assembled by hand at release time, which is where the
schedule pain lives. The point of the artifact chain is that it can be **derived**.

## Step 0 — read or set the evidence profile

"Evidence is a link, never a description" says nothing about what the link must point
*at*. Before producing anything, establish the **evidence profile** this project runs
at — read it from `.evidence/context/compliance.md`'s `evidence_profile` field if it is
already set; if it is not, set it there now so every later skill reads the same answer
instead of re-deciding it per change.

| Level | Adds | Typical floor |
| --- | --- | --- |
| L0 | Machine output only — CI logs, structured test reports | Internal tooling, Tier 1 |
| L1 | + screenshot on failure | Tier 1 production paths (recommended default) |
| L2 | + screenshot at every step of manual and regulated execution | Tier 2, and Tier 3 workflows with no signature involved |
| L3 | + video for critical workflows, and signed attestation on manual results | Tier 3 — audit trail, signatures, record integrity |

**Default: L1.** Raise to **L2** for anything `risk-tiering` marks Tier 2 or above, and
to **L3** for Tier 3. A customer validation package typically expects **L2 as the
floor**, and **L3 wherever a signature or audit-trail control depends on the evidence**
— a screenshot proves the workflow was exercised; a signed attestation proves a named
human verified the result and cannot later disclaim it.

**Screenshot requirements, when the profile calls for one.** In frame: the record
identifier, a timestamp, the logged-in user (or role), and an environment banner that
distinguishes test from production. Named `<tracker-key>-<test-case-id>-<step-n>.png`.
Stored under `validation/evidence/<tracker-key>/`. The traceability row's
`evidence_link` column cites this path directly — a real path a reviewer can open,
never a description of what the screenshot would have shown.

Record the profile once, in `.evidence/context/compliance.md`, e.g.
`evidence_profile: L2, raised to L3 for Tier 3`. `test-strategy` and `testrail-authoring`
read it from there too; do not let three skills each guess at it independently.

## Step 1 — know what you owe

Read `.evidence/context/compliance.md`. The frameworks that apply determine the
deliverables. Do not produce a validation package for a project with no validation
obligation, and do not produce a generic report for one that owes named protocols.

Common shapes:

| Framework family | Deliverables typically owed |
| --- | --- |
| GxP / computerised system validation | URS, FRS, design specification, risk assessment, IQ/OQ/PQ protocols and executed evidence, traceability matrix, validation summary report |
| Medical device software | Requirements and design records, unit/integration/system verification evidence, SOUP inventory, risk file linkage, release record with residual anomalies |
| Trust services / certification audits | Evidence that controls **operated** over a period, dated, with the actor recorded |
| Data protection | Processing records, impact assessments, rights-request capability evidence, transfer mechanism records |
| None declared | Traceability and test evidence still stand on their own merits |

## Step 2 — the mapping from artifact chain to deliverable

| SDLC artifact | What it feeds |
| --- | --- |
| `intent.md` | Change request / user need |
| `spec.md` requirement IDs | Requirement specification entries |
| `spec.md` design section and diagrams | Design specification |
| `spec.md` control table | Control evidence per framework |
| `plan.md` test plan rows | Test case identification |
| Test case IDs and run results | Executed verification evidence |
| PR, approver, timestamp | Change control and review record |
| Deployment record | Installation / release evidence |

## Step 3 — what to produce per change

1. **Change-impact assessment.** Which existing requirements are added, modified or
   retired; whether the change is in regulatory scope; and its risk classification. If
   it is out of scope, say why in one sentence — that sentence is itself evidence.
2. **Traceability rows** in `validation/traceability.csv`, append-safe. Never rewrite
   rows for requirements you did not touch.
3. **Re-verification call.** No re-verification, partial (named tests only), or full,
   justified against the risk classification.
4. **Customer-facing note** where customers place your changes into their own change
   control.

## Step 4 — at release

Export, do not assemble. If a deliverable cannot be exported from the chain, that is a
gap in the chain, not a reason to write it by hand — writing it by hand is how the two
diverge.

## Rules

- **Evidence is a link** — a commit, a test run, a PR, a signed record. Never a
  description.
- A requirement with no covering test gets a row saying `NO COVERAGE`. Do not soften it;
  it is a blocking release finding.
- Never mark a requirement verified because the code looks right. Verified means a test
  ran, passed, and you can point at the run.
- For audits testing whether a control **operated over a period**, design evidence is not
  enough. Every control needs a dated artifact showing it ran.
- The named owner approves the package. You assemble and flag; you do not sign.
- A manual or regulated result must meet the evidence profile in force (Step 0) — a
  bare pointer is not enough where the profile calls for a screenshot, a video, or a
  signed attestation.

## The number worth tracking

Time to assemble the evidence package at release. If the chain is working this collapses
from a project to an export, and it is usually the clearest return this framework
produces.
