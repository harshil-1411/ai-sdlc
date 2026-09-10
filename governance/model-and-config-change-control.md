# Change control: model versions and agent configuration

Owner: Engineering Platform. Approver: QA/RA for anything affecting a regulated path.

The instructions that steer the agent are part of the development environment. When
they change, the environment changed. Treat them accordingly.

## What is under change control

| Item | Where | Change record required |
| --- | --- | --- |
| Model version / tier | managed settings, CI env | Yes |
| Claude Code minimum version floor | `requiredMinimumVersion` | Yes |
| Skills | `plugins/*/skills/**` | Yes — policy owner signs |
| Hooks and gate scripts | `plugins/*/hooks`, `scripts/` | Yes |
| Managed settings | `managed-settings.json` | Yes |
| `CLAUDE.md` | repo root | No — reviewed as code |
| Templates | `templates/` | No — reviewed as code |

## The acceptance test is the eval suite

A model upgrade or configuration change is accepted when the eval suite passes at or
above the current threshold. The suite is 20–50 real tasks from recent work with their
accepted outcomes, plus one permanent case per past incident.

```
change proposed → eval suite runs → pass rate compared to baseline
   → pass: merge with the run recorded on the PR
   → drop: reviewed before merge; a drop on a regulated-path case blocks
```

This is what makes "we control our AI configuration" an evidenced claim rather than an
assertion. Without it you cannot answer what changed when behaviour changes.

## Version floor

`requiredMinimumVersion` in managed settings refuses to start Claude Code below an
approved floor, so the controls are enforced by a build the organisation has assessed.
Raise it deliberately: assess, run evals, then raise.

## Model upgrades

1. Platform team pins the new model in a non-production configuration.
2. Eval suite runs against both old and new. Differences are examined, not just the
   pass rate.
3. Regulated-path cases are examined individually regardless of aggregate score.
4. QA/RA notified with the comparison; approval recorded.
5. Rollout, with the previous pin retained for rollback.

Record model changes in the change log even when behaviour appears unchanged. "We did
not notice a difference" is not evidence; the eval run is.
