# Definition of Ready / Done — tiered

Apply the `risk-tiering` skill first. Ceremony scales with risk; it does not apply
uniformly. A nine-gate DoR on every change recreates the process weight this framework
exists to remove.

The tier is recorded once, in `.evidence/changes/<KEY>/state.json` (via
`evidence change start <KEY> --tier <n>`) and as a `Risk tier: <n>` line in spec.md and
plan.md. `evidence change status <KEY>` shows which rows below are still missing.

Where a row says "per compliance.md", the frameworks, controls and sign-off roles come
from `.evidence/context/compliance.md`. If it names none, the row is N/A with that
reason; if it is missing, the row is an `[ASK]`, not a skip.

## Ready

| Item | T1 | T2 | T3 |
| --- | --- | --- | --- |
| Problem and affected users stated | ● | ● | ● |
| Acceptance stated in verifiable terms | ● | ● | ● |
| `plan.md` on disk, approved by a human (`/evidence-sdlc:approve`) | ● | ● | ● |
| `intent.md` committed | ○ | ○ | ● |
| `spec.md` with requirement IDs | ○ | ● | ● |
| API / data model impact understood | ○ | ● | ● |
| Test scenarios identified | ○ | ● | ● |
| Regulatory control impact assessed (frameworks per compliance.md) | ○ | ○ | ● |
| Validation package impact assessed | ○ | ○ | ● |
| Security impact assessed | ○ | ○ | ● |
| Rollback plan named | ○ | ○ | ● |
| Sign-off roles per compliance.md aware | ○ | ○ | ● |

## Done

| Item | T1 | T2 | T3 |
| --- | --- | --- | --- |
| Merged via PR, code owner approved | ● | ● | ● |
| Build, tests, lint green with output attached | ● | ● | ● |
| Diff matches `plan.md` (or plan updated in the same commit) | ● | ● | ● |
| `security-reviewer` run recorded, pass clean | ○ | ● | ● |
| `verifier` run recorded | ● | ● | ● |
| `code-reviewer` run recorded | ○ | ○ | ● |
| Docs and release note updated | ○ | ● | ● |
| Compliance review pass clean | ○ | ○ | ● |
| Traceability rows updated | ○ | ○ | ● |
| Revalidation call recorded | ○ | ○ | ● |
| ADR in `.evidence/decisions/` for each lasting design decision, linked from spec.md | ○ | ○ | ● |
| Eval case added under `evals/` (if a new skill was introduced) | ○ | ○ | ○ |
| Sign-offs required by compliance.md attached | ○ | ○ | ● |

● required   ○ not required

**Do not** enforce Done with an agent's own assertion. Each ● is evidenced by a link:
a CI run, a PR approval, a commit, a signed record.

A new skill is not Done without at least one eval case under its plugin's `evals/`
directory — see `evals/README.md`'s `case.yaml`/`prompt.md`/`graders/` convention.
The row above shows `○` at every tier because it is conditional on introducing a new
skill, not on tier, the same way the ADR row is conditional on a design decision
having been made.
