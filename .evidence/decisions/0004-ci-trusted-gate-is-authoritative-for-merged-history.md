# 0004. CI's trusted gate is authoritative for what merges

Status: Proposed
Date: 2026-09-24
Deciders: Suparn Bector (maintainer); second approver Harshil (Tier 3)
Tracker: PILOT-58   Spec: intent/2026-09-24-integrity-monitor-hardening/spec.md
Supersedes: none
Superseded-by:

Stored at `.evidence/decisions/NNNN-<slug>.md`. Numbers are never reused. An accepted
ADR is never edited except to change its Status or set Superseded-by — a changed
decision is a new ADR.

## Context
- Local hooks see the repository the agent controls. The second security design review showed that a local push-time commit check can be defeated:
  - editing remote-tracking refs (F6);
  - evil merges (F7);
  - pushing refs other than HEAD, tags, or `push.default=matching` (F8);
  - committing rolled-back audit logs or records with `commit-tree` (F9).
- CI's `sign-and-gate` job runs on GitHub's machines:
  - it has the key (a repository secret);
  - it uses the **base branch's** CLI (`../trusted`), not the PR's;
  - it knows the true base and head SHAs from the pull-request event;
  - branch protection on `main` requires it.

  The agent can influence none of that.

## Decision
The trusted CLI gains `evidence verify-range --base <sha> --head <sha>`. `sign-and-gate` runs it with `github.event.pull_request.base.sha` and `head.sha`, and fails the job on any problem. It checks:
1. **Every commit in `base..head`, merges included.**
   - Changed paths come from `diff-tree -r --root --name-status` per commit, plus `--cc` for merges.
   - The net `diff --name-status base..head` is checked as well.
   - All of A, M, D, T and R are checked against the claims of the change's **approved** plan: the plan whose sha256 matches the signed `approval.json`, read at the head.
2. **Every commit message** carries the change key and an `Agent-Session:` trailer, or is a human commit by a CODEOWNER (identified by the GitHub API author, not the git author field).
3. **Secrets:** every added blob is scanned in chunks. A blob over the cap fails the job unless its path is on the org allow-list.
4. **Audit logs:** each `.evidence/audit/*.jsonl` at the head verifies (signatures with the key, chain, replay and session rules). Across the range, each committed version of a log is a byte-prefix of the next.
5. **Change records:** `.evidence/changes/<key>/{state,approval}.json` at the head verify, and the state is not missing when history shows the change was started.

The local push gate keeps its existing checks as **fast feedback**. Docs say plainly that it is advisory against a determined agent, and that `sign-and-gate` is the control.

## Consequences
- Easier: the merge-time guarantee holds however the commits were made, and doesn't depend on local state.
- Harder:
  - problems surface at PR time, not push time;
  - `ci.yml` must change, which is change-controlled: the implementing session is started with `CHANGE_TICKET=PILOT-58`.
- Constrained: `main` protection must keep requiring `sign-and-gate`, and admins bypassing it (`enforce_admins=false`) is a known owner risk.
- Review trigger: reopen if the product must work without a CI system the organisation controls.

## Alternatives
| Option | Why it lost |
| --- | --- |
| A local push-time range check (ADR-0003 first draft) | Its inputs are agent-writable locally |
| A GitHub required status from a separate app | More infrastructure; `sign-and-gate` already has the key, the trusted CLI and the true SHAs |
