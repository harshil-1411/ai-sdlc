# Definition of Ready / Done — tiered

Apply the `risk-tiering` skill first. Ceremony scales with risk; it does not apply
uniformly. A nine-gate DoR on every change recreates the process weight this framework
exists to remove.

## Ready

| Item | T1 | T2 | T3 |
| --- | --- | --- | --- |
| Problem and affected users stated | ● | ● | ● |
| Acceptance stated in verifiable terms | ● | ● | ● |
| Approved `plan.md` on disk | ● | ● | ● |
| `intent.md` committed | ○ | ● | ● |
| `spec.md` with requirement IDs | ○ | ● | ● |
| API / data model impact understood | ○ | ● | ● |
| Test scenarios identified | ○ | ● | ● |
| Part 11 control impact assessed | ○ | ○ | ● |
| Validation package impact assessed | ○ | ○ | ● |
| Security impact assessed | ○ | ○ | ● |
| Rollback plan named | ○ | ○ | ● |
| QA/RA aware | ○ | ○ | ● |

## Done

| Item | T1 | T2 | T3 |
| --- | --- | --- | --- |
| Merged via PR, code owner approved | ● | ● | ● |
| Build, tests, lint green with output attached | ● | ● | ● |
| Diff matches `plan.md` (or plan updated in the same commit) | ● | ● | ● |
| Security review pass clean | ○ | ● | ● |
| Docs and release note updated | ○ | ● | ● |
| Compliance review pass clean | ○ | ○ | ● |
| Traceability rows updated | ○ | ○ | ● |
| Revalidation call recorded | ○ | ○ | ● |
| ADR stored (if a design decision was made) | ○ | ○ | ● |
| QA/RA sign-off attached | ○ | ○ | ● |

● required   ○ not required

**Do not** enforce Done with an agent's own assertion. Each ● is evidenced by a link:
a CI run, a PR approval, a commit, a signed record.
