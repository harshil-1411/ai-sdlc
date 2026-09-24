# Change control: model versions and agent configuration

Owner: Engineering Platform. Approver: QA/RA for anything affecting a regulated path.

The instructions that steer the agent are part of the development environment. When
they change, the environment changed. Treat them accordingly.

## What is under change control

| Item | Where | Change record required |
| --- | --- | --- |
| Model version / tier | **Owner action:** the shipped `managed-settings.json` does **not** pin a model. If you control the model centrally, add the managed `model` setting (and record it in CI env for eval runs). Until you do, engineers choose the model. | Yes, once pinned |
| Claude Code minimum version floor | `requiredMinimumVersion` in `managed-settings.json` | Yes |
| Gate policy | `plugins/evidence-sdlc/policy/default-policy.json`; your org policy (`EVIDENCE_ORG_POLICY` or `evidence-policy.json` in the managed-settings directory); each repo's `.evidence/policy.json` | Yes |
| Gate engine and hooks | `plugins/evidence-sdlc/scripts/engine/`, `plugins/*/hooks/hooks.json` | Yes |
| Skills and agents | `plugins/*/skills/**`, `plugins/*/agents/**` | Yes — policy owner signs |
| Managed settings | `managed-settings.json` | Yes |
| `CLAUDE.md` | repo root | No — reviewed as code |
| Templates | `templates/` | No — reviewed as code |

## How configuration changes are controlled

Each layer below is a distinct mechanism. Note which are enforced and which depend on
you turning them on.

| Control | What it does | Status | Proof |
| --- | --- | --- | --- |
| Org policy, tighten-only merge | The default policy, then the org policy (may change anything), then the repo's `.evidence/policy.json`, which may only tighten: lists are unioned, strictness flags OR-ed, and ungated paths can only shrink unless the org sets `allow_repo_ungated_additions`. A repository cannot loosen what the organisation set. | Enforced by the engine | `engine-tests.py` cases V2X-01* |
| Control-plane protection | No agent tool (Edit/Write/Bash, any form) may write `.claude/settings*.json`, `.claude/hooks/**`, `.claude/agents/**`, `.evidence/policy.json`, `.evidence/secrets-allowlist.json`, approval/state records, `.evidence/audit/**`, `managed-settings.json`, `.mcp.json`, or user-level Claude settings and plugin directories. Configuration is therefore changed by a human, outside the agent. | Enforced by the engine | cases V2G-09* |
| Configuration is source | Policy JSON, hooks, CI workflows and other non-markdown files are gated source: changing them in an agent session needs an approved plan (cases V2G-03*, V2G-04*), and CI workflow paths need a `CHANGE_TICKET` and at least Tier 2 (cases V2G-08*, V2S-02*). Skill and agent **markdown** is ungated by the engine and relies on review. | Enforced (non-markdown); review (markdown) | as cited |
| Engine regression suite | `python3 plugins/evidence-sdlc/scripts/tests/engine-tests.py` — every case labelled with its requirement ID, every v1 audit probe included. A change to the engine or default policy must keep it green. | Runs locally; in CI once enabled | the suite itself |
| Plugin version-bump check | CI fails if a plugin's files change without a version bump in its `plugin.json`, so deployed configuration is identifiable by version. | CI — **owner enables** `.github/workflows/ci.yml` on the host | REQ-V2P-01, REQ-V2P-05 |
| Eval suite | `plugins/*/evals/` via `claude plugin eval`; results summarised in each plugin's `evals/SUMMARY.md`. Tests skill/agent behaviour, not the gates. | Manual dispatch (needs an API key and calls the model); not a per-commit gate | REQ-V2E-01 |
| Merge approval | Server-side branch protection and CODEOWNERS on the hosting platform. | **Owner action** — authoritative | — |

## The acceptance test for behaviour changes is the eval suite

A model upgrade or a skill/agent change is accepted when the eval suite passes at or
above the current threshold. The suite is real tasks with accepted outcomes, plus one
permanent case per past incident.

```
change proposed → eval suite runs (manual dispatch) → pass rate compared to baseline
   → pass: merge with the run recorded on the PR
   → drop: reviewed before merge; a drop on a regulated-path case blocks
```

This is what makes "we control our AI configuration" an evidenced claim rather than an
assertion — provided the run is actually dispatched and recorded. Nothing forces that
run automatically; make it a required PR checklist item for configuration changes.
Gate behaviour is covered separately, and deterministically, by the engine regression
suite above.

## Version floor

`requiredMinimumVersion` in managed settings refuses to start Claude Code below an
approved floor, so the controls run on a build the organisation has assessed. Raise it
deliberately: assess, run evals, run the canary (every session must print "Evidence
Chain gates live"), then raise.

## Model upgrades

1. Platform team pins the new model (managed `model` setting) in a non-production
   configuration.
2. Eval suite runs against both old and new. Differences are examined, not just the
   pass rate.
3. Regulated-path cases are examined individually regardless of aggregate score.
4. QA/RA notified with the comparison; approval recorded.
5. Rollout, with the previous pin retained for rollback.

Record model changes in the change log even when behaviour appears unchanged. "We did
not notice a difference" is not evidence; the eval run is. If you have not pinned a
model, record that decision here instead: model changes then arrive with Claude Code
updates and the version floor is your only lever.
