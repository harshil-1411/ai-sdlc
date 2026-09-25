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
   - The change key is the single key in the PR head branch name, read from `$GITHUB_EVENT_PATH` and never interpolated into `run:`.
   - Every non-merge commit's message carries that key, plus either an `Agent-Session:` trailer or a `Human-Commit: <github login>` trailer. There is no exception based on who the author is.
   - That change's state at the head is verified and not `released`, and it is not released at the base.
   - **Approval comes from GitHub:** an `APPROVED` review on the **head SHA** by a user who owns every changed path. Ownership is taken from the last matching rule in the base's `.github/CODEOWNERS`. Team owners are unsupported and fail. The approver must not be the PR author.
   - The claims are read from the plan whose sha256 matches the head's `approval.json`. The signature is also checked, but the merge decision does not rest on it alone. The approving review covers every commit in the range, including `Human-Commit:` commits.
2. **Paths:**
   - Every commit in `base..head` is checked, with `diff-tree -r -M --root --name-status`, plus `--cc -M` for merges and the net diff `diff -M base...head`.
   - Every A/M/D/T/R path outside `.evidence/**` is checked against the claims.
   - **Merge commits:** a merge whose `--cc` output is empty and whose non-first parent is reachable from the base (a clean "Update branch" merge of `main`) passes without trailers. Any other merge is checked like a commit, and needs the key and a trailer.
   - `.evidence/**` is exempt from claims and judged only by rules 4–5.
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
   - Records of **other** changes may change only by a signed release (stage → `released`) or a signed clear (violations `open` → closed with `cleared_by`).
6. **Re-run after approval.** `pull_request_target` does not fire on reviews. The same base-branch workflow accepts `workflow_dispatch` with a PR number, and the job can be re-run from the PR's checks. The owner re-runs it after approving.
7. **Push report mode.** On `push` to `main`, `verify-range --push-report` runs over `event.before..event.after`. It checks rules 2–5, with claims taken from each commit's change key where one is present; it reports and never blocks. An all-zero `before` (first push) is skipped with a note. This catches admin direct pushes after the fact.

### Revision 3 (code review of the implementation, 2026-09-25)
These refine the rules above. Each is tested in `cli-lifecycle-tests.py` "REQ-IMH-19 …".
- **"Exists at the base" means where the branch left it** (`git merge-base base head`). The tip of
  `main` holds records and logs that other PRs added after this branch started; their absence at
  the head is not a deletion. "Released at the base" still reads the tip, so a key released
  meanwhile can't be reused.
- **Merges, rule 4:** a log must be a byte-prefix extension of the merge's **first** parent. For
  the other parents, every line must still be present. No byte-prefix of both sides can exist when
  both appended to the same shared log, such as `clear-violations.jsonl`. Resolve such a conflict
  with the branch's lines first. One *session's* log appended on both sides still fails, because
  its hash chain forks by more than one step. That shape is not supported (PILOT-59).
- **Merges, rule 5:** a merge is judged against its first parent, and a record whose merged
  version is exactly a non-first parent's, where that parent is in the base, came in with an
  update from the base and is not this PR's change.
- **Rule 1 binds the records to the change:** `state.json` and `approval.json` under
  `.evidence/changes/<KEY>/` must carry `key: <KEY>`, so another change's signed approval, copied
  across, can't lend its plan's claims.
- **Every git failure fails the rule it was feeding.** An absent path and a failed git call are
  told apart.
- **Re-run after approval (rule 6)** is "Re-run jobs" on the PR's `pull_request_target` run. A
  `workflow_dispatch` run re-checks the PR but is attached to the dispatching branch's commit, so
  it doesn't satisfy the PR's required check.
- **Name-matched required checks.** A PR-branch workflow with a job named `verify-range` could post
  a passing check under that name. The mitigations are code-owner review of `.github/**` (which the
  approving review then covers), pinning the requirement to this workflow file with a ruleset
  where the host supports it, and the engine's denial of agent workflow dispatches from another
  ref.
- **Whole-range checks, whatever the commit shape** (security review). Per-commit checks can be
  sidestepped by a record or log that is renamed away in one commit and added back in another, or
  by a crafted merge. So, from the merge-base to the head:
  - every audit log keeps every line it had;
  - every change record obeys the same transition rules as a single commit, unless its head
    version equals the base tip's.

  All diffs run with `--no-renames`.
- **An "update from the base" parent must be newer than what the branch had**: in the base, and
  descending from where the branch's first parent meets the base. A merge of an old base commit is
  judged like any commit.
- **Claims exempt only `.evidence/audit/`, `.evidence/changes/` and `.evidence/violations/`**,
  which rules 4–5 judge. `.evidence/policy.json`, the secrets allow-list and `.evidence/context/`
  must be claimed like source.
- **Rule 0 also fails a PR whose base is not the default branch**, read from the event. The
  workflow re-runs on `edited`, so a retargeted PR is checked again. Reviews are read across every
  page.
- **Push report (rule 7) is best-effort against admins:** it runs the pushed commit's own workflow
  and CLI, so a direct push can alter the report that should catch it.
- **`Human-Commit:` commits** carry no audit-log requirement. They have no agent session, and the
  head-commit code-owner review covers them.

### Third-review trace
| Finding | Where it is closed |
| --- | --- |
| N1 PR runs its own workflow | `pull_request_target` base-branch workflow (Decision; spec REQ-IMH-21) |
| N2 author-based exception | Rule 1: no author exception; `Human-Commit:` + head-SHA review |
| N3 omitted, deleted or rolled-back records | Rules 4–5 |
| N4 key compromise forges approval | Rule 1: approval from a GitHub review; ADR-0003 §4 corrected |
| N5 no key / fork PRs | Rule 0: fail closed |
| N6 old key replay | Rule 1: single key from the head branch, not released at base or head |
| N7 two-dot net diff | Rule 2: `base...head` |
| N8 PR-controlled policy / allow-lists | Rule 0: read from the base |
| N9 push and dispatch events | Rules 0, 7 and event conditions in REQ-IMH-21 |
| N10 fail-open bootstrap guard | No guard: `pull_request_target` uses `main`'s workflow, so PILOT-58's own PR isn't gated |

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
