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

Paths are relative to `plugins/evidence-sdlc/` unless stated. "Cases V2x-NN*" are
the labelled regression cases in `plugins/evidence-sdlc/scripts/tests/engine-tests.py`
that prove the control; run the suite to reproduce. Engine controls act on the agent
inside a Claude Code session and fail closed (cases V2G-01*); they are
defence-in-depth, not a substitute for server-side controls. Confirm they are live in
each deployment with the session-start canary ("Evidence Chain gates live").

| # | Risk | Control | Where it lives |
| --- | --- | --- | --- |
| R1 | Agent produces plausible but incorrect code that passes review | Feedback loop (build/test/lint) before "done" (guided by skills); `git push` / `gh pr create` denied until the tier's review agents have run — verifier (T1), + security-reviewer (T2), + code-reviewer (T3) — as recorded in the audit log (cases V2S-04*); review agents are write-denied (cases V2K-03*); risk-tiered human review depth | `agents/verifier.md`, `skills/risk-tiering`, `scripts/engine/` |
| R2 | Agent weakens or deletes the test that would have caught a defect | Engine test protection, switched on by state rather than an env var: after `evidence change advance <KEY> failing-test` on an approved fix, every test file that existed at the recorded `fix_base` commit is denied edit or deletion by any tool, including Bash (`rm`, `sed -i`, `git checkout --`, opaque writes). New test files are allowed. Proof: `engine-tests.py` cases V2G-10*, V2G-02* | `scripts/engine/evidence_policy.py`, `policy/default-policy.json` (test globs) |
| R3 | Agent changes a validated workflow without change control | Engine change-control gate: case-insensitive policy globs (migrations, CI workflows, infra/terraform/helm/k8s, audit, signing, crypto, validation) require a human-set `CHANGE_TICKET` matching `change_ticket_pattern`; tier floors deny an under-tiered change on auth/crypto/audit/migrations (T3) and CI/infra/payments (T2). Bash writes are held to the same rules. The agent cannot set the ticket itself (settings are control plane). Proof: cases V2G-08*, V2S-02*, V2G-02*, V2G-09*. Limit: the path list is policy — validated paths outside it must be added to your org or repo policy | `scripts/engine/`, `policy/default-policy.json` |
| R4 | Human approval becomes theatre because review volume exceeds capacity | Risk tiering; review-depth metric; quarterly spot-audit of approvals against diffs | `skills/risk-tiering`, `baseline-metrics.md` |
| R5 | Model or configuration changes silently alter agent behaviour | Pinned minimum version (`requiredMinimumVersion`); model pin via managed `model` setting (owner action — not pinned in the template); agents cannot edit settings/policy/hooks (cases V2G-09*); repo policy may only tighten org policy (cases V2X-01*); engine regression suite; eval suite as acceptance test (manual dispatch); change record for model upgrades | `model-and-config-change-control.md` |
| R6 | Untrusted content (customer documents, tickets, external PRs) carries injected instructions | Trust-boundary skill; no agent reads customer production documents; injection checks in review | `skills/agent-trust-boundaries` |
| R7 | Secrets or customer data reach the tool | Managed-settings deny rules, sandbox credential denial and network allowlist (owner replaces the placeholder domains); narrow git allows with denies for `git -c`, `git config`, `git show :path`. Engine secret scanner denies secrets in written content, Bash command text, heredoc bodies and staged diffs without echoing the value; dangerous git config keys (`core.hooksPath`, `credential.*`, `alias.*` …) are denied. Proof: cases V2K-01*, V2K-02*. Limit: pattern-based detection does not catch every format; customer data is kept out by environment policy, not by a scanner | `managed-settings.json`, `scripts/engine/secretscan.py` |
| R8 | Traceability gaps between requirement and evidence | Artifact chain committed to git; key required in every agent commit message; `evidence gaps` / `export` build the matrix, with `approved_by` and `agent_sessions` columns | `skills/evidence-package`, `evidence` CLI; cases V2G-07* |
| R9 | Agent obtains a route to approve its own work | Approval is human-only by construction: written by the UserPromptSubmit hook from a human-typed `/evidence-sdlc:approve <KEY> <sha>` (the model cannot author a user prompt), by `evidence approve` in the human's own terminal (requires a TTY, refuses inside Claude Code), or by a verified approving GitHub review. The approval binds to the plan's sha256. The engine denies an agent running `evidence approve` (except GitHub mode), `change set-tier` or `change release`, writing `approval.json`/`state.json`, pushing to protected refs, or merging (`gh pr merge`, `gh api` merge/protection). Proof: cases V2A-01*, V2G-09*, V2G-05*; self-approval attempts appear in `evidence metrics`. Limits: local approver identity is the machine's `git user.email`, not cryptographic; **server-side branch protection + CODEOWNERS with no agent on the code-owner list is the authoritative control and is an owner action** | `scripts/engine/`, hosting-platform settings |

## 4. Residual risk statement

<To be completed. State the residual risk after controls, the acceptance decision, and
who accepted it.>

## 5. Boundaries — what the tool is NOT approved for

- Access to production databases, production credentials, or customer documents.
- Direct commits to protected branches. (Agent pushes to protected refs are denied by
  the engine, cases V2G-05*; server-side branch protection is the authoritative
  control.)
- Autonomous production deployment. (Recognised deploy commands against a production
  or computed target are denied without a human-set `RELEASE_APPROVAL`, cases
  V2G-06*; recognition is by a policy list of tools, so a deploy path it does not know
  is not caught — your deploy system's own approvals remain the control.)
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
