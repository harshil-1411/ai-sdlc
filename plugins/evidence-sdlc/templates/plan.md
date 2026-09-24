# Plan: <short title>
Tracker: <KEY>   From: spec.md   Date: <yyyy-mm-dd>
Risk tier: <1|2|3> — <one-line reason; name any policy tier floor that applies>

Approval is not written in this file. A human records it with `/evidence-sdlc:approve <KEY> <plan-sha>`
(or `evidence approve <KEY>` in their own terminal, or an approving review in GitHub
mode); it binds to this file's hash, so any edit after approval voids it.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Files claimed
<One glob per line, repo-relative (e.g. `src/billing/**`, `tests/billing/test_invoice.py`).
These are enforced: once approved, an edit outside these globs is denied. Claim what
the plan touches — tests and docs included — and no more. `evidence change start`
reports overlap with other active changes' claims; if it does, stop and sequence the
two changes — see codebase-grounded-planning's "Concurrent sessions" section.>

## Files that change
<Real, verified paths only. New files: the directory must already exist.>

## Order of work
1.
2.
3.
<Mark which steps are independent — those can run in parallel worktrees.>

## Mid-flight checkpoint (Tier 2/3)
<Name which numbered step above is marked `CHECKPOINT` — the point where execution
stops and re-confirms the work so far against spec.md before continuing (see
codebase-grounded-planning's "While implementing" section). Required for Tier 2/3.
Write `N/A — Tier 1` when this plan is Tier 1.>

## Reuse decisions
<What existing module/endpoint/component this extends, and why anything new is new.>

## Risks
<What this could break. Which step is riskiest. Rollback for each.>

## Proof
See the test plan section (from the `test-strategy` skill).

| REQ ID | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- |

## Considered and rejected
<Options not taken, with the reason.>
