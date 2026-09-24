---
name: release-readiness
description: Decide whether a release candidate is ready — pre-release checklist, drafted test summary report, rollback rehearsal evidence, open defects and required sign-offs — and hand the go/no-go to a human. Use when someone says "release", "ship it", "go/no-go", "cut a release", "rollback plan", "ready to deploy", or asks whether a build can go out. The agent drafts evidence; it never signs, approves, or supplies a release approval.
---

# Release readiness (Stage 4: Release)

A release is a decision made by named people on linked evidence. This skill assembles the
evidence and names the gaps. It never makes the decision.

## Precondition

Read `.evidence/context/deployment.md`, `test-strategy.md` and `compliance.md`. If
`deployment.md` does not name the deploy system and its approval step, STOP and ask —
you cannot describe a release path you have not confirmed.

## Checklist

Dispatch the `release-manager` agent with the release scope (tracker keys or a commit
range). It returns blockers, a draft test summary report, rollback status and approvals.
Check its report against this list; every item is evidenced by a link, not an assertion.

| # | Item | Evidence |
| --- | --- | --- |
| 1 | Every change in scope is at `verified` (`evidence change status <KEY>`) | state.json per change |
| 2 | Required review-agent runs are recorded for each change's tier | audit log entries |
| 3 | Build and tests green on the exact commit being released | CI run link |
| 4 | Test summary report drafted from `evidence-quality`'s `templates/test-summary-report.md`, every figure linked | report file |
| 5 | Exit criteria from `test-strategy.md` met, or each gap accepted by a named person | report rows |
| 6 | No open defect above the agreed severity without a recorded accept decision | tracker links |
| 7 | Rollback procedure exists for each data, schema, infrastructure or contract change, **and was rehearsed** | run log or CI job with date and environment |
| 8 | Traceability rows updated; `evidence gaps` shows no `NO COVERAGE` for in-scope requirements | command output |
| 9 | Release note and docs updated (`docs-writer` agent if not) | commit links |
| 10 | Sign-offs required by `compliance.md` and the tier are identified, with who holds each | approvals table |

A rollback that was written but never run is item 7 **not met**. Say so plainly.

## Rules

- **Draft, never sign.** Leave the test summary report's Decision section, every
  "Accepted by" and every signature blank. Those are completed by the named humans.
- **Deploy only through the deploy system's own approvals.** Name the step from
  `deployment.md` (for example a protected environment, a change-advisory approval, or a
  pipeline manual gate) and hand off to it. Never run a deploy command yourself to
  "save a step", and never bypass a pipeline gate.
- **Never supply `RELEASE_APPROVAL`** or any other release-authorisation value, and
  never suggest one. It carries a human's approval reference; an agent-supplied value
  converts a control into a fiction.
- **No quiet downgrades.** Do not relabel a failed or unrun check as "known issue" or
  "flaky" to clear the list. Report it as a blocker with who can clear it.

## Output

1. **Go/no-go blockers** — each with its evidence gap and the person who can clear it.
2. **Checklist** — the table above with a status and link per row.
3. **Draft test summary report** — path to the drafted file, Decision section blank.
4. **Hand-off** — the deploy system's approval step and the humans who must sign.

## Done means

The humans who decide have one page with every item linked, every gap named, and the
Decision section waiting for them. When the release is deployed and a human confirms
it, `evidence change advance <KEY> released` records it for each change in scope.
