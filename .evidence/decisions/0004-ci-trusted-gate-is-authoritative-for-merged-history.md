# 0004. A base-branch `pull_request_target` gate is authoritative for what merges

Status: Proposed (revision 2, after the third security design review, 2026-09-24)
Date: 2026-09-24
Deciders: Suparn Bector (maintainer); second approver Harshil (Tier 3)
Tracker: PILOT-58   Spec: intent/2026-09-24-integrity-monitor-hardening/spec.md
Supersedes: none
Superseded-by:

Stored at `.evidence/decisions/NNNN-<slug>.md`. Numbers are never reused. An accepted
ADR is never edited except to change its Status or set Superseded-by — a changed
decision is a new ADR.

## Context
- Local hooks see a repository the agent controls. A local push-time commit check can be defeated through refs, merges, pushed refs other than HEAD, and `commit-tree` (second review F6–F9).
- **The existing `ci.yml` does not escape that.** On `pull_request`, GitHub runs the workflow file from the PR itself (third review N1). A PR can delete a step, repoint `../trusted`, or replace the `sign-and-gate` job, and a required check by that name is still satisfied.
- **A `pull_request_target` workflow runs the base branch's version of the workflow file**, with the base's secrets and token. It is safe as long as it never checks out or executes PR code. Reading PR objects with git plumbing (`fetch refs/pull/N/head`, `rev-list`, `diff-tree`, `cat-file`) executes nothing from the PR.
- The HMAC key is symmetric and shared between hooks and CI (docs/managed-settings.md), so records signed with it can't be the sole basis for merge decisions if the local key is ever exposed (ADR-0003 §4).

## Decision
A new workflow, `.github/workflows/verify-range.yml`, runs on `pull_request_target` (opened, synchronize, reopened) with `permissions: contents: read, pull-requests: read`.
- It checks out **only the base** (the trusted CLI) and fetches `refs/pull/<n>/head` as objects.
- It runs `evidence verify-range --base <event.pull_request.base.sha> --head <event.pull_request.head.sha> --pr <n>`.
- Its job, `verify-range`, is a **required status check** on `main`, set by the owner.

`verify-range`:
0. **Fails closed on bad input:**
   - SHAs that are empty or not hexadecimal;
   - a missing key or one under 32 characters (a `None` from `signing.verify` counts as a failure);
   - no GitHub token.

   Fork and Dependabot PRs fail by design. The CLI reads policy, allow-lists and CODEOWNERS **from the base SHA**, never from the head.
1. **Change and approval:**
   - The change key is the single key in the PR head branch name (from the event). Every commit's message must carry it and an `Agent-Session:` trailer. There is no exception for commits authored by a code owner.
   - That change's state at the head must be verified and not `released`, and it must not be released at the base.
   - **Approval comes from GitHub:** an `APPROVED` review on the head SHA by a CODEOWNER (from the base's `.github/CODEOWNERS`) who is not the PR author. The claims are read from the plan whose sha256 matches the head's `approval.json`. The signature is checked, but the merge decision does not rest on it alone.
2. **Paths:** every commit in `base..head` is checked, with `diff-tree -r -M --root --name-status`, plus `--cc` for merges and the net diff `base...head`. Every A/M/D/T/R path is checked against those claims. `.evidence/**` is judged by rules 4–5, not exempted.
3. **Secrets:** added blobs are scanned in 1 MiB chunks with overlap. A blob over the cap fails unless its path is on the org allow-list.
4. **Audit logs:**
   - Every `Agent-Session` named in the range has its log at the head, and it verifies.
   - No audit log that exists at the base is deleted or type-changed.
   - For every commit, each audit log is a byte-prefix extension of that log in every parent.
5. **Change records:**
   - `state`, `approval` and violations records at the head verify.
   - None that exists at the base is deleted or type-changed.
   - The `state` stage never moves backwards across the range.
   - No violation that was open at the base, or earlier in the range, is missing or closed without a signed clear.

On `push` to `main`, the same command runs over `event.before..event.after` and reports. This catches admin direct pushes after the fact, and does not block.

The existing `sign-and-gate` job (results signing and `gaps --strict`) is unchanged.

## Consequences
- Easier:
  - the merge guarantee holds however the commits were made, whatever the PR does to its own workflows, and whether or not the local key is exposed (approval from GitHub);
  - PILOT-58's own PR is naturally not gated, because the workflow isn't on `main` yet, so no bootstrap guard is needed. It's enforced from the next PR.
- Harder:
  - every PR needs an approving CODEOWNER review, which branch protection already requires;
  - the owner must add the new required check;
  - fork PRs can't merge through this gate.
- Constrained:
  - `enforce_admins=false` still lets admins bypass. The `push` run records that, but doesn't prevent it;
  - required code-owner review of `.github/**` stays essential: the workflow can only be changed by a PR that a code owner approves.
- Review trigger: reopen if the product must work without a CI the organisation controls, or when PILOT-61 isolates the key.

## Alternatives
| Option | Why it lost |
| --- | --- |
| A step in the existing `pull_request` `sign-and-gate` | Runs the PR's own workflow file, so the PR can remove the gate (N1) |
| A local push-time range check | Its inputs are agent-writable locally |
| Approval from the signed `approval.json` alone | The key is symmetric and exposure is an accepted residual risk (ADR-0003 §4), so GitHub reviews are independent of it |
| An exception for commits authored by a CODEOWNER | GitHub's author login follows the commit's email, and agent commits carry the maintainer's identity (N2) |
