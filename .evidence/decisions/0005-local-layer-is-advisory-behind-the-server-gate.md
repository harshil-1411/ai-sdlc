# 0005. The local layer is advisory behind the server gate

Status: Proposed
Date: 2026-09-25
Deciders: Suparn Bector (maintainer); second approver Harshil (Tier 3)
Tracker: PILOT-62   Spec: intent/2026-09-25-local-layer-advisory/spec.md
Supersedes: none   Relies on: ADR-0003 rev. 2, ADR-0004 rev. 3
Superseded-by:

Stored at `.evidence/decisions/NNNN-<slug>.md`. Numbers are never reused. An accepted
ADR is never edited except to change its Status or set Superseded-by — a changed
decision is a new ADR.

## Context
- ADR-0004 makes the base-branch `verify-range` job plus code-owner review authoritative for what merges. ADR-0003 §4 states that local checks can be defeated by a determined agent.
- Even so, the local layer still costs human round trips for events that are not the agent's doing, or that it has already undone:
  - restored control-plane changes stay open violations;
  - edits by the human or by Claude Code to user configuration during a call are recorded against the agent;
  - Tier 3 in `acceptEdits` and `auto` needs a machine-local org-policy loosening.
- The owner decided on 2026-09-25 that the local layer should be advisory in practice.

## Decision
1. **A verified undo closes the violation.** When the monitor restores or removes a control-plane change and re-reading confirms the undo, the violation is recorded closed (`resolved: "restored"`). It is kept in the signed record and the audit log. This is bounded per session (`auto_resolve_max_per_session`, default 3). `verify-range` rule 5 accepts such entries, shows them to the code owner, and fails any other entry that is closed at birth without a signed clear.
2. **Config edits are judged by effect, not author.**
   - `settings.local.json`: permission grants and tightening, plus listed display keys, are kept. Anything else, including every key that runs commands, is undone.
   - System-managed files are not charged when the session's user could not have written them (not owned, not writable).
   - `~/.claude.json` is charged only when its MCP or tool-permission projection changes.
3. **Tier 3 auto modes follow a fact on GitHub.** `acceptEdits` and `auto` are allowed for Tier 3 when the engine reads, through the pinned `gh`, that `verify-range` is a required check on the default branch **pinned to the GitHub Actions app**. The result is cached in a signed temp file. `bypassPermissions` and `dontAsk` stay denied. The org policy can switch this off, and a repository policy can only switch it off.
4. **Posting commit statuses or check runs** from an agent session is denied locally (`check-forgery`). A required check that is matched by name only can be satisfied by a commit status anyone with the token can post, which is why decision 3 requires the app pin.
   - **What the app pin does not prove** (revised after review, 2026-09-25): a check run from app 15368 only shows that *some* GitHub Actions workflow produced it. A `workflow_dispatch` of `verify-range.yml` with `--ref <agent branch>` runs that branch's copy of the workflow and CLI and attaches its result to the branch head, and a `pull_request` workflow on the agent's branch can name a job `verify-range`. Both produce an app-15368 check run under the required name.
   - **The real control** is code-owner review of `.github/**` and of the PR's head commit, plus a workflow fix: `verify-range.yml` refuses `workflow_dispatch` from any ref other than `refs/heads/main` and always runs the base's CLI. That fix is a human change to a change-controlled file; the proposed diff is in `HANDOFF.md`. The engine also denies an agent dispatching a workflow from another ref and re-running workflow runs.

## Consequences
- No human clear is needed for undone changes or for the owner's own configuration edits. Tier 3 works in `auto` mode wherever the server gate is in force.
- The local layer gains no authority: everything it now tolerates is either undone or visible to `verify-range`, which is unchanged in rules 0–3 and tightened in rule 5.
- A new dependency: GitHub's branch-protection API shape. It fails closed (deny) when unreachable or unexpected.
- The gate is bound to the repository being edited: its `origin` remote must be `approval.github_repo` on github.com. Gate detection runs only a `gh` the session's user could not have replaced (the org policy's `ci_gate_gh_path`, or a root-owned `gh` first on PATH), with `GH_HOST` pinned and a gh configuration that neither redirects the API (`http_unix_socket`) nor names another host.
- Owner actions:
  - pin `verify-range` to GitHub Actions in branch protection;
  - set `approval.github_repo`;
  - keep the org policy root-owned.

## Alternatives
| Option | Why not |
| --- | --- |
| An owner-set flag asserting that the gate is required | Unchecked, and goes stale when protection changes; doesn't prove the app pin |
| A repository `.evidence/policy.json` flag | Agent-writable; repository policy is tighten-only |
| Exempt all user control-plane paths | `~/.claude.json` and `settings.local.json` can register MCP servers and hooks |
| Delete restored violations | Loses the record that `verify-range` and auditors read |
| Release record written by CI on merge (in this change) | Needs CI writes to protected `main` and a human-authored workflow; deferred (PILOT-63) |
