# Plan: Pilot fix-round — six issues found running Evidence Chain on a real repo

Tracker: PILOT-1..6   From: pilot session findings (no intent.md/spec.md — this is a
maintenance fix to the framework itself, not product work)   Approved by: suparn.bector@msbdocs.com
(via direct, itemized fix instructions in the pilot report)   Date: 2026-09-12

## Files that change

- `plugins/evidence-discovery/skills/stack-discovery/SKILL.md` (PILOT-1)
- `plugins/evidence-discovery/skills/toolchain-discovery/SKILL.md` (PILOT-1, PILOT-6)
- `plugins/evidence-discovery/skills/design-system-discovery/SKILL.md` (PILOT-1, PILOT-6)
- `plugins/evidence-discovery/skills/compliance-discovery/SKILL.md` (PILOT-1, PILOT-6)
- `plugins/evidence-sdlc/skills/spec-and-design/SKILL.md` (PILOT-2, PILOT-4)
- `plugins/evidence-sdlc/skills/codebase-grounded-planning/SKILL.md` (PILOT-2)
- `plugins/evidence-discovery/hooks/hooks.json` (PILOT-3)
- `plugins/evidence-quality/hooks/hooks.json` (PILOT-3)
- `plugins/evidence-sdlc/hooks/hooks.json` (PILOT-3)
- `plugins/evidence-sdlc/scripts/preflight.sh` (new) (PILOT-3)
- `SECURITY.md` (PILOT-3)
- `plugins/evidence-sdlc/skills/risk-tiering/SKILL.md` (PILOT-4)
- `plugins/evidence-integrations/skills/integration-change/SKILL.md` (PILOT-5)
- `.claude/settings.json` (infra: relax `EVIDENCE_ISSUE_KEY_PATTERN`, no real tracker exists yet for this repo)
- `plan.md` (this file — satisfies `gate-plan-exists.sh` for the `.sh` edits above)

## Order of work

1. PILOT-1: stack-discovery loses to documentation — rewrite description, add Rule 0,
   add "do not offer, run" to all four discovery skills. Independent.
2. PILOT-2: hard precondition (stop, not warn) on spec-and-design and
   codebase-grounded-planning when no stack profile exists. Independent.
3. PILOT-3: hooks fail open when a gate script isn't executable — invoke every hook
   via `bash` instead of direct exec; add `preflight.sh`; document in SECURITY.md.
   Independent.
4. PILOT-4: risk-tiering and spec-and-design didn't trigger on direct design asks —
   extend descriptions, add "state the tier before design" rule. Depends on PILOT-2
   touching the same spec-and-design file (sequenced, not blocking).
5. PILOT-5: integration-change didn't trigger on a third-party API — extend
   description, clarify it runs alongside secure-api-review. Independent.
6. PILOT-6: cross-check every SKILL.md for the same vocabulary gap; extend the three
   discovery siblings touched in PILOT-1. Independent.

All six are independently reviewable; each fix is its own commit.

## Reuse decisions

No new modules. Every fix edits an existing skill's frontmatter `description` and/or
adds a small rule section to its body, or (PILOT-3) adds one new gate-adjacent script
that reuses the same jq-based SessionStart JSON shape as `session-context.sh` and
`require-repo-profile.sh`. No parallel implementation was introduced anywhere.

## Risks

- Broadening trigger phrasing in descriptions could cause over-triggering on unrelated
  requests. Mitigated by keeping additions narrowly scoped to the literal phrasings
  named in the pilot report rather than generic broadening.
- The `bash`-wrapper change in PILOT-3 touches every hook invocation in three plugins;
  a typo would silently disable a gate. Mitigated by validating every hooks.json with
  `python3 -m json.tool` and by re-running the fail-open simulation (chmod -x, invoke
  via bash, confirm deny) after the change.
- `preflight.sh` must not itself fail open when the environment is degraded (missing
  jq, or missing basic coreutils). Mitigated by writing it with bash builtins only
  (no `cat`/`dirname`/`sed`/`tr`/`find` dependency) so it degrades to a plain-JSON
  fallback rather than to silence.
- Rollback for any step: `git revert` the single commit for that fix; each fix is
  isolated to its own commit.

## Proof

No automated test suite exists for this framework's own skills/hooks (this repo has
no CI configured — see `.evidence/context/toolchain.md`). Proof is the manual
verification script the pilot report specifies: JSON validity, shell syntax,
frontmatter presence, the `bash`-prefix grep, `preflight.sh` behavior with and without
`jq` on PATH, the fail-open simulation on `gate-plan-exists.sh`, and a grep for
reintroduced stack hardcoding. Each is run and its result reported, not assumed.

| REQ ID | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- |
| PILOT-3-01 | Manual (hook behavior) | No | — | — | fail-open simulation output in session transcript |
| PILOT-3-02 | Manual (script behavior) | No | — | — | `preflight.sh` output with/without `jq` on PATH |

## Considered and rejected

- Bypassing `require-issue-key.sh` with `--no-verify`: rejected — the user explicitly
  chose to relax `EVIDENCE_ISSUE_KEY_PATTERN` instead, since no real tracker exists for
  this repo yet, rather than skip the gate outright.
- Leaving `gate-plan-exists.sh` unsatisfied and editing `.sh` files anyway: rejected —
  this is exactly the "note the gate and proceed anyway" failure PILOT-2 exists to stop.
  Writing this plan.md is the in-spirit fix, not a workaround.
