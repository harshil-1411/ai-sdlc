# Plan: Testing depth across every test type, and a test-strategy interview at onboarding
Tracker: PILOT-51   From: spec.md   Approved by: suparn.bector@msbdocs.com (maintainer)   Date: 2026-09-24

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

No concurrent plan claims any of these paths: `git worktree list` shows only this
worktree on `master`. The other plans on disk (`intent/2026-09-12-gate-regression-tests/plan.md`,
`intent/2026-09-19-arxiv-inspired-sdlc-improvements/plan.md`) claim evidence-sdlc
scripts, templates and skills. None of them overlaps with the paths below. Files with
uncommitted user edits (`git status`) are excluded on purpose.

## Files claimed
New:
- `plugins/evidence-discovery/skills/test-strategy-discovery/SKILL.md`
- `plugins/evidence-discovery/templates/test-strategy.md`
- `plugins/evidence-quality/skills/performance-testing/SKILL.md`
- `plugins/evidence-quality/skills/security-testing/SKILL.md`
- `plugins/evidence-quality/skills/static-analysis/SKILL.md`
- `plugins/evidence-quality/skills/e2e-ui-testing/SKILL.md`
- `plugins/evidence-quality/skills/e2e-ui-testing/references/playwright.md`
- `plugins/evidence-quality/skills/e2e-ui-testing/references/selenium.md`
- `plugins/evidence-quality/skills/e2e-ui-testing/references/cypress.md`
- `plugins/evidence-quality/skills/accessibility-testing/SKILL.md`
- `plugins/evidence-quality/templates/test-summary-report.md`
- `plugins/evidence-discovery/evals/test-strategy-discovery-*/` (3 cases)
- `plugins/evidence-quality/evals/{performance-testing,security-testing,static-analysis,e2e-ui-testing,accessibility-testing}-*/` (15 cases)

Changed:
- `plugins/evidence-quality/skills/test-strategy/SKILL.md`
- `plugins/evidence-quality/skills/continuous-testing/SKILL.md`
- `plugins/evidence-quality/skills/test-automation/SKILL.md`
- `plugins/evidence-quality/agents/test-designer.md`
- `plugins/evidence-quality/templates/test-plan-section.md`
- `plugins/evidence-discovery/scripts/require-repo-profile.sh`
- `plugins/evidence-quality/.claude-plugin/plugin.json`
- `plugins/evidence-discovery/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `plugins/evidence-quality/evals/README.md`
- `plugins/evidence-discovery/evals/README.md`
- `README.md`
- `docs/skills-reference.md`
- `docs/getting-started.md`

## Files that change
All "Changed" paths above exist and were read this session (test-strategy,
continuous-testing, test-automation, test-designer, test-plan-section,
require-repo-profile.sh, both plugin.json, marketplace.json, both evals READMEs, in
full; README.md, skills-reference.md, getting-started.md, by grep for the lines
listing skills). Parent directories of every new file exist:
`plugins/evidence-discovery/skills/`, `plugins/evidence-discovery/templates/`,
`plugins/evidence-quality/skills/`, `plugins/evidence-quality/templates/`, and both
`evals/` directories. Both `evals/` directories are currently untracked in git; new
cases are added beside the existing ones and are not committed separately from them.

## Order of work
1. **[independent]** `test-strategy-discovery/SKILL.md` + `templates/test-strategy.md`.
   (REQ-TSD-01, -02, -03)
2. **[independent]** `performance-testing/SKILL.md`. (REQ-PERF-01..03)
3. **CHECKPOINT.** Re-read spec.md against steps 1–2: are the house conventions
   (profile first, no assumed tool, blocks vs informs, evidence as link, "Never")
   applied in a form the remaining four skills can copy? Record any drift here
   before continuing.
4. **[independent]** `security-testing/SKILL.md`. (REQ-SEC-01..03)
5. **[independent]** `static-analysis/SKILL.md`. (REQ-SA-01, -02)
6. **[independent]** `e2e-ui-testing/SKILL.md` + three references. (REQ-E2E-01, -02)
7. **[independent]** `accessibility-testing/SKILL.md`. (REQ-A11Y-01)
8. **[depends on 1–7]** Integrate: `test-strategy` (profile read, layer table,
   functional coverage, test summary report), `continuous-testing` (profile read,
   stage table, pre-release evidence), `test-automation` (flake detection, pointer
   to e2e-ui-testing), `test-designer` (non-functional routing),
   `test-plan-section.md`, new `test-summary-report.md`.
   (REQ-TSD-04, REQ-COV-01, REQ-FLK-01, REQ-TSR-01, -02, REQ-INT-01)
9. **[independent]** `require-repo-profile.sh` message text. (REQ-TSD-05)
10. **[depends on 1–7]** 18 eval cases. (REQ-TEVAL-01)
11. **[depends on 1–9]** Docs and metadata. (REQ-DOC-01)
12. Verify: `bash -n` + run `require-repo-profile.sh` with and without a profile
    and confirm exit 0 and valid JSON; `jq .` on edited JSON; frontmatter check on every
    new SKILL.md; grep each REQ's acceptance marker; `claude plugin eval` on the new
    cases with `--runs 1` if the maintainer approves the cost.

## Mid-flight checkpoint (Tier 2/3)
Step 3 is marked `CHECKPOINT`.

Checkpoint result (2026-09-24): steps 1–2 checked against spec.md. REQ-TSD-01..03
and REQ-PERF-01..03 are met by named sections. All five house conventions are present in both
files and are used as the pattern for steps 4–7. No drift.

## Reuse decisions
- Discovery skill and template follow `toolchain-discovery` / `stack-discovery`:
  read before asking, `[confirmed]/[inferred]/[ASK]`, and a template in
  `evidence-discovery/templates/`.
- Evidence artifacts use the existing L0–L3 evidence profile (`evidence-package`),
  not a new one.
- Eval cases follow the existing `prompt.md` + `graders/` convention (`tool_used`
  graders for trigger and non-trigger cases, `llm` graders for behavior).
- Tool-specific depth uses a `references/` directory, loaded on demand, rather than
  bloating SKILL.md.

## Risks
- **Riskiest step: 8.** It edits the three most-used quality skills, and a wording
  change could weaken an existing rule (e.g. the flake retry ban). Mitigation: edits
  are additive insertions; existing rules keep their wording; review the diff for any
  removed line. Rollback: revert the file.
- **Step 9** touches a SessionStart script. Only the message string changes; `bash -n` and a
  live run confirm exit 0 and valid JSON. Rollback: revert the file.
- **Trigger collisions** (spec, Areas of concern): measured by the non-trigger evals.

## Proof
This repository has no CI or test-management tool (`toolchain.md` `[ASK]`). Available
layers: `claude plugin eval` and direct shell execution.

| REQ ID | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- |
| REQ-TSD-01 | eval (trigger) | Yes | `test-strategy-discovery-fires-on-onboarding-question` | evals dir | eval run output |
| REQ-TSD-02 | manual — content review | No | — | template diff | PR review |
| REQ-TSD-03 | eval (behavior) | Yes | `test-strategy-discovery-out-of-scope-needs-decider` | evals dir | eval run output |
| REQ-TSD-04 | manual — content review | No | — | skill diffs | PR review |
| REQ-TSD-05 | shell | Yes | — | `bash -n` + live run of `require-repo-profile.sh` | command output |
| REQ-PERF-01, -03 | eval (trigger) + review | Yes | `performance-testing-fires-on-load-test-request` | evals dir | eval run output |
| REQ-PERF-02 | eval (behavior) | Yes | `performance-testing-refuses-to-invent-target` | evals dir | eval run output |
| REQ-SEC-01, -03 | eval (trigger) + review | Yes | `security-testing-fires-on-dast-request` | evals dir | eval run output |
| REQ-SEC-02 | eval (behavior) | Yes | `security-testing-suppression-needs-owner-and-expiry` | evals dir | eval run output |
| REQ-SA-01 | eval (trigger) | Yes | `static-analysis-fires-on-lint-baseline-request` | evals dir | eval run output |
| REQ-SA-02 | eval (behavior) | Yes | `static-analysis-refuses-to-disable-rule-to-pass` | evals dir | eval run output |
| REQ-E2E-01 | eval (trigger) | Yes | `e2e-ui-testing-fires-on-playwright-request` | evals dir | eval run output |
| REQ-E2E-02 | eval (behavior) | Yes | `e2e-ui-testing-does-not-assume-a-tool` | evals dir | eval run output |
| REQ-A11Y-01 | eval (behavior) | Yes | `accessibility-testing-automated-scan-is-not-enough` | evals dir | eval run output |
| REQ-COV-01, REQ-FLK-01, REQ-TSR-01, -02, REQ-INT-01 | manual — content review | No | — | skill/template diffs | PR review |
| REQ-DOC-01 | manual — content review | No | — | doc diffs | PR review |
| REQ-TEVAL-01 | shell | Yes | — | count of new case dirs = 18, each with prompt.md + graders/ | command output |

Non-trigger case per skill, each asserting the skill does not fire:
`*-no-fire-on-*` (6 cases), evidence = eval run output.

## Considered and rejected
See spec.md "Rejected alternatives". Additionally: splitting into six PILOT keys
(one per skill). Rejected because the integration step (8) and docs step (11) touch
the same files for all six, and splitting would serialise them for no review benefit.

## Verification result (2026-09-24)
- Shell: `bash -n` and live runs of `require-repo-profile.sh` with and without a
  profile, both exit 0 with valid JSON; `jq` parses all six manifests; frontmatter
  `name` matches the directory for all six new skills; all 23 REQ acceptance markers
  are found by grep; 18 complete eval case directories.
- Evals (`claude plugin eval`, `--runs 1 --ablation none`): 18/18 score 1.0.
  Reports: `plugins/evidence-quality/evals/results/2026-09-24T01-43-18-198Z/` and
  `plugins/evidence-discovery/evals/results/2026-09-24T01-44-24-010Z/`. Cost $2.18.
- Single runs show that each skill works, not how reliably it triggers. Run the default
  3 runs with a baseline arm before relying on trigger rates.

## Amendment (2026-09-24) — examples and a missed doc
Found on review after verification. Same REQ-DOC-01, which is widened to include examples:
- `docs/gates-reference.md` — the `require-repo-profile.sh` entry quotes the
  message text changed in step 9. Update the quote.
- `examples/scenarios/test-strategy-and-release-cycle/README.md` (new) — a worked
  scenario covering onboarding interview → profile → a change with performance,
  accessibility, E2E and security requirements → the plan's test section → CI placement
  → the test summary report.
- `examples/README.md` — list the new scenario.
Also `README.md`'s scenario list (found while verifying).
Claimed paths: the four above. No overlap with other plans.
