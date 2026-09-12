# Plan: <short title>
Tracker: <KEY>   From: spec.md   Approved by: <engineer>   Date: <yyyy-mm-dd>

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Files claimed
<Every path this plan is going to touch, so a concurrent session in another
worktree can see it is already spoken for before it starts. Same list as "Files
that change" below, checked here BEFORE work starts. If another plan/<key>.md
already claims one of these paths, stop and sequence the two changes instead of
proceeding — see codebase-grounded-planning's "Concurrent sessions" section.>

## Files that change
<Real, verified paths only. New files: the directory must already exist.>

## Order of work
1.
2.
3.
<Mark which steps are independent — those can run in parallel worktrees.>

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
