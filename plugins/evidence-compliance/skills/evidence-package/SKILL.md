---
name: evidence-package
description: Derive the compliance evidence deliverables a project owes — traceability matrices, change-impact assessments, validation or qualification records, audit evidence — from the committed artifact chain instead of assembling them by hand at release. Use this whenever a change is specced or merged, whenever a release is prepared, whenever anyone mentions traceability, revalidation, an audit, a certification, or evidence for a customer, and whenever a control is claimed without a pointer behind it.
---

# Evidence package

Compliance evidence is usually assembled by hand at release time, which is where the
schedule pain lives. The point of the artifact chain is that it can be **derived**.

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

## The number worth tracking

Time to assemble the evidence package at release. If the chain is working this collapses
from a project to an export, and it is usually the clearest return this framework
produces.
