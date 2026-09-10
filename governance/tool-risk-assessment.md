# Risk assessment: AI coding tooling in the SDLC

Owner: QA/RA (approver) with Engineering Platform (author)   Review cycle: annual, or on
any change to the categories below   Status: TEMPLATE — must be completed and signed
before agent-authored code reaches a customer-facing release.

> This is the document an inspector or a customer's supplier-quality auditor asks for
> first. Every other control in this repository is downstream of the position taken here.
> Complete it with your regulatory counsel; do not ship it as written.

## 1. What the tool is

Claude Code is an agentic development tool used by the organisation engineers to author,
review and test source code. It does not execute in, connect to, or form part of the
the organisation production system. It does not process customer regulated records in the
course of development. It is development-environment software.

## 2. GAMP 5 categorisation and rationale

Proposed position: **supporting / development software, not a GxP computerised system
subject to full CSV.**

Rationale to be recorded here:
- The tool does not create, modify, maintain, archive, retrieve or transmit electronic
  records subject to a predicate rule.
- Its output — source code — is subject to the existing verification controls of the
  SDLC: automated test, human code-owner review, and the release validation package.
- Assurance therefore derives from **verification of the output**, not qualification of
  the generator. This is the same logic already applied to compilers, IDEs, build tools
  and static analysers in this SDLC.

State explicitly which existing SOP this parallels, and have QA/RA confirm the parallel
holds under your quality system.

## 3. Risks and the controls that address them

| # | Risk | Control | Where it lives |
| --- | --- | --- | --- |
| R1 | Agent produces plausible but incorrect code that passes review | Mandatory feedback loop (build/test/lint) before "done"; verifier subagent with fresh context; risk-tiered human review depth | `agents/verifier.md`, `skills/risk-tiering` |
| R2 | Agent weakens or deletes the test that would have caught a defect | `block-test-weakening` hook denies test edits during fix tasks | `scripts/block-test-weakening.sh` |
| R3 | Agent changes a validated workflow without change control | `protect-validated-paths` hook requires a change ticket | `scripts/protect-validated-paths.sh` |
| R4 | Human approval becomes theatre because review volume exceeds capacity | Risk tiering; review-depth metric; quarterly spot-audit of approvals against diffs | `skills/risk-tiering`, `baseline-metrics.md` |
| R5 | Model or configuration changes silently alter agent behaviour | Pinned minimum version; eval suite as acceptance test; change record for model upgrades | `model-and-config-change-control.md` |
| R6 | Untrusted content (customer documents, tickets, external PRs) carries injected instructions | Trust-boundary skill; no agent reads customer production documents; injection checks in review | `skills/agent-trust-boundaries` |
| R7 | Secrets or customer data reach the tool | Managed settings deny rules, sandbox credential denial, network allowlist | `managed-settings.json` |
| R8 | Traceability gaps between requirement and evidence | Artifact chain committed to git; traceability rows generated per change | `skills/evidence-package` |
| R9 | Agent obtains a route to approve its own work | Branch protection; distinct agent identity in CI; no agent on the code-owner list | `deviation-capa-runbook.md`, CI config |

## 4. Residual risk statement

<To be completed. State the residual risk after controls, the acceptance decision, and
who accepted it.>

## 5. Boundaries — what the tool is NOT approved for

- Access to production databases, production credentials, or customer documents.
- Direct commits to protected branches.
- Autonomous production deployment.
- Any use inside the product itself. **If an agent is embedded in the product
  (e.g. an agent acting on customer records inside the product), that is a different system, a
  GxP computerised system, and requires its own full validation. This assessment does
  not cover it.**

## 6. Approval

| Role | Name | Signature | Date |
| --- | --- | --- | --- |
| Author — Engineering Platform | | | |
| Reviewer — Head of Engineering | | | |
| Approver — QA/RA | | | |
| Reviewer — Information Security | | | |
