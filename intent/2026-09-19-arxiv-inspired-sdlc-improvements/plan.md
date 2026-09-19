# Plan: Three arXiv-inspired SDLC process improvements
Tracker: PILOT-50   From: spec.md   Approved by: suparn.bector@msbdocs.com (maintainer)   Date: 2026-09-19

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

No concurrent plan claims any of these paths: `git worktree list` shows only this
worktree, `git branch -a` shows only `master`, and the only other `plan.md` on disk
(`intent/2026-09-12-gate-regression-tests/plan.md`, tracker TRACE-1) claims
`plugins/evidence-sdlc/scripts/tests/gate-regression-tests.sh` and
`validation/traceability.csv` — no overlap with the paths below.

## Files claimed
- `plugins/evidence-sdlc/skills/risk-tiering/SKILL.md`
- `plugins/evidence-sdlc/skills/codebase-grounded-planning/SKILL.md`
- `plugins/evidence-sdlc/templates/plan.md`
- `plugins/evidence-sdlc/templates/definition-of-ready-and-done.md`
- `docs/extending.md`
- `plugins/evidence-sdlc/scripts/template-sensor.sh`
- `plugins/evidence-sdlc/scripts/tests/template-sensor-tests.sh`
- `plugins/evidence-sdlc/evals/risk-tiering-debt-raises-tier/` (new directory)
- `plugins/evidence-sdlc/evals/codebase-grounded-planning-writes-checkpoint-for-tier2/` (new directory)

## Files that change
- `plugins/evidence-sdlc/skills/risk-tiering/SKILL.md` — existing file, verified
  (108 lines, read in full during spec-and-design).
- `plugins/evidence-sdlc/skills/codebase-grounded-planning/SKILL.md` — existing file,
  verified (98 lines, read in full).
- `plugins/evidence-sdlc/templates/plan.md` — existing file, verified (37 lines).
- `plugins/evidence-sdlc/templates/definition-of-ready-and-done.md` — existing file,
  verified (contains tiered `## Done` table with existing conditional row pattern,
  e.g. "ADR stored (if a design decision was made)").
- `docs/extending.md` — existing file, verified ("Adding a new skill" section read,
  no existing eval-requirement cross-reference).
- `plugins/evidence-sdlc/scripts/template-sensor.sh` — existing file, verified in full
  (advisory-only PostToolUse sensor, always exits 0).
- `plugins/evidence-sdlc/scripts/tests/template-sensor-tests.sh` — existing file,
  verified (regression suite for template-sensor.sh, `run_case` helper already
  present, pattern confirmed reusable).
- `plugins/evidence-sdlc/evals/risk-tiering-debt-raises-tier/{prompt.md,case.yaml,graders/}`
  — new, directory `plugins/evidence-sdlc/evals/` already exists (29 sibling cases).
- `plugins/evidence-sdlc/evals/codebase-grounded-planning-writes-checkpoint-for-tier2/{prompt.md,case.yaml,graders/}`
  — new, same existing parent directory.

## Order of work

1. **[independent]** Edit `risk-tiering/SKILL.md`: insert a technical-debt
   classification paragraph in the "Tiers" section, after the Tier 1 definition
   (after line 31) and before "When in doubt, tier up" (line 33) — the same place a
   supplementary classification rule already reads naturally alongside the three tier
   definitions. Wording: name concrete signals (documented workarounds, prior
   incidents referenced in git history or a known-issues doc if one exists, thin test
   coverage in the touched area), state debt only raises the effective tier by one
   notch, never lowers it, and never exceeds Tier 3 — mirroring the existing override
   rule's "never weaken a tier's ceiling" language so the two rules read consistently.
   (REQ-DEBT-01, REQ-DEBT-02, REQ-DEBT-03)

2. **[independent]** Edit `codebase-grounded-planning/SKILL.md`'s "While implementing"
   section (lines 64–76): add a bullet instructing that for Tier 2/3 work, when
   execution reaches the step marked `CHECKPOINT` in `plan.md`'s "Order of work," stop
   and re-confirm the work so far still matches `spec.md`'s requirements and the
   plan's stated scope before continuing, recording any drift the same way plan
   drift is already recorded per the existing first bullet. (REQ-CKPT-02)

3. **[independent]** Edit `templates/plan.md`: add a new section "## Mid-flight
   checkpoint (Tier 2/3)" between "## Order of work" (line 17–21) and "## Reuse
   decisions" (line 23), with placeholder text instructing: name which numbered step
   in "Order of work" is marked `CHECKPOINT` and required for Tier 2/3 (mark `N/A —
   Tier 1` when not applicable). (REQ-CKPT-01)

4. **[independent]** Edit `templates/definition-of-ready-and-done.md`'s `## Done`
   table: add a conditional row "Eval case added under `evals/` (if a new skill was
   introduced)" with the same `○ ○ ○` non-mandatory-by-default styling as the existing
   "ADR stored (if a design decision was made)" row, since both are conditional on a
   fact about the specific change rather than the tier alone. Add one sentence
   pointing at `evals/README.md`'s case.yaml/prompt.md/graders/ convention so the row
   is not a dangling requirement with no named mechanism. (REQ-EVAL-01)

5. **[independent]** Edit `docs/extending.md`'s "1. Adding a new skill" section: add a
   short subsection (after "Body conventions," before "Agent frontmatter") named
   "Eval coverage" stating that a new skill is not Done until at least one eval case
   exists under the plugin's `evals/` directory (cross-referencing the
   `definition-of-ready-and-done.md` row added in step 4 and `evals/README.md`'s
   existing convention — trigger, non-trigger, behavior cases). (REQ-EVAL-01)

6. **[depends on 1–5 landing, since it references their exact section names]** Edit
   `template-sensor.sh`: add two more `case "$base"` branches following the exact
   existing pattern (read tool input, resolve path, extract section body via the same
   `awk` idiom, never fail closed, never deny):
   - `plan.md` (and the namespaced `plan/<KEY>.md` form, already handled by the
     existing parent-dir check) — in addition to the existing "Files claimed" stub
     check, also read the sibling `spec.md` in the same directory (if present), grep
     it for `Risk tier: 2` or `Risk tier: 3`, and if found, check the "Order of work"
     section body for the literal string `CHECKPOINT` (case-insensitive). Fire an
     advisory note if the tier is 2/3 and no `CHECKPOINT` marker is present. Silent if
     no sibling `spec.md`, sibling is Tier 1, or the marker is present. (REQ-CKPT-03)
   - `SKILL.md` under `plugins/*/skills/*/` — derive the plugin root and skill name
     from the path, check whether `plugins/<plugin>/evals/` contains any directory
     whose name starts with `<skill-name>-`; fire an advisory note if it does not (or
     if the plugin has no `evals/` directory at all). Silent otherwise. (REQ-EVAL-02)

7. **[depends on 6]** Extend `template-sensor-tests.sh` with new `run_case` calls
   covering: a Tier 2/3 plan.md with a `CHECKPOINT` marker (silent), a Tier 2/3
   plan.md without one (finding), a Tier 1 plan.md without one (silent), a plan.md
   with no sibling spec.md (silent), a new SKILL.md with a matching eval case
   directory present (silent), and one without (finding). Run
   `bash plugins/evidence-sdlc/scripts/tests/template-sensor-tests.sh` and confirm
   all pass, including the pre-existing cases (regression check).

8. **[independent, can run alongside 1]** Add
   `plugins/evidence-sdlc/evals/risk-tiering-debt-raises-tier/` (`prompt.md`,
   `case.yaml`, `graders/`) following the existing 29-case pattern in this
   directory: a `behavior`-tagged case presenting a change to a module described as
   carrying documented workarounds and thin test coverage, asserting risk-tiering
   states a tier one notch above what the change would get on its own (and does not
   exceed Tier 3).

9. **[independent, can run alongside 2]** Add
   `plugins/evidence-sdlc/evals/codebase-grounded-planning-writes-checkpoint-for-tier2/`
   (`prompt.md`, `case.yaml`, `graders/`): a `behavior`-tagged case asking for a plan
   for a Tier 2 change, asserting the produced `plan.md` names a `CHECKPOINT` step in
   "Order of work."

10. Run `bash -n` on `template-sensor.sh` (CONTRIBUTING.md's own validation
    standard) and `claude plugin eval . --tag behavior --case
    risk-tiering-debt-raises-tier --case
    codebase-grounded-planning-writes-checkpoint-for-tier2 --runs 1` for the two new
    eval cases before calling this plan done.

Steps 1–5 and 8–9 are independent of each other and can run in parallel; step 6
depends on 1–5 landing (it references their section text by name); step 7 depends on
6; step 10 is the final verification pass.

## Reuse decisions
- Extends the existing advisory-sensor pattern in `template-sensor.sh` rather than
  adding a new gate script or hook — the sensor already reads `plan.md`/`spec.md` and
  extracts named sections by heading; the two new checks are additional `case`
  branches in the same script, not a parallel mechanism.
- Extends the existing `evals/` convention (`case.yaml`/`prompt.md`/`graders/`,
  `claude plugin eval`) rather than inventing a new test format for the two new
  behavior cases.
- Extends the existing conditional-row pattern in
  `definition-of-ready-and-done.md` ("ADR stored (if...)") rather than adding a new
  table or a new document.
- No new gate script, no new external dependency, no new file format — consistent
  with intent.md's "Additive only" constraint.

## Risks
- **Highest risk: `template-sensor.sh` silently becoming a gate.** The sensor's
  entire safety property is "always exits 0." A mistake in step 6 (e.g. an added
  `jq -e` check whose failure trips `set -e`, or a stray non-zero exit path) would
  turn an advisory hook into an undocumented deny. Mitigation: step 7's regression
  suite explicitly re-runs all pre-existing cases, and the new code follows the
  existing script's `command -v jq >/dev/null 2>&1 || exit 0` / `[ -z "$path" ] &&
  exit 0` degrade-to-silence idiom rather than introducing a new failure path.
  Rollback: revert `template-sensor.sh` to its current committed state; the other
  five files are independent markdown edits with no coupling to this risk.
- **Sensor's plan/spec pairing is a heuristic, not a guarantee.** Step 6 assumes
  `spec.md` sits next to `plan.md` in the same directory. This holds for the
  `intent/<slug>/{spec.md,plan.md}` and repo-root `{spec.md,plan.md}` layouts seen in
  this repo, but not for the `plan/<TRACKER-KEY>.md` namespaced form (`gate-plan-
  exists.sh`'s own comments confirm that form has no fixed sibling-spec location).
  The check silently degrades to silence when it can't find a sibling spec — consistent
  with the sensor's existing "nothing to protect here" philosophy — rather than
  guessing. Documented as a known limitation in the sensor's own header comment
  (step 6).
- **Riskiest single step is 6** (script logic, not prose) — reviewed line-by-line
  against the existing `awk`/`jq` idiom before merge, per Tier 3's "second reviewer
  independently examines the regulated portion" requirement (here: the gate-adjacent
  script, not a regulated record, but the same reviewer-depth requirement applies per
  risk-tiering's table since this is a change to the framework's own gates).
- Steps 1–5, 8–9 (markdown/eval-case additions) carry low risk: exempt from
  `gate-plan-exists.sh`'s source gate (markdown extension), no runtime behavior
  change beyond text future sessions read.

## Proof
See the test plan section (from the `test-strategy` skill). This repo has no CI and
no test-management tool of its own (`toolchain.md`, `[ASK]` open questions 3) — the
two automated layers available are `claude plugin eval` (LLM-graded skill behavior)
and direct `bash` execution of the regression-test scripts already in this repo.

| REQ ID | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- |
| REQ-DEBT-01 | eval (behavior) | Yes | `risk-tiering-debt-raises-tier` | `plugins/evidence-sdlc/evals/risk-tiering-debt-raises-tier/` | `claude plugin eval` run output |
| REQ-DEBT-02 | eval (behavior) | Yes | `risk-tiering-debt-raises-tier` | same case — asserts named signals, not a new artifact | same run output |
| REQ-DEBT-03 | eval (behavior) | Yes | `risk-tiering-debt-raises-tier` | same case — asserts "one notch," never exceeding Tier 3 | same run output |
| REQ-CKPT-01 | manual — content review | No | — | `templates/plan.md` diff | PR review of the template diff |
| REQ-CKPT-02 | eval (behavior) | Yes | `codebase-grounded-planning-writes-checkpoint-for-tier2` | `plugins/evidence-sdlc/evals/codebase-grounded-planning-writes-checkpoint-for-tier2/` | `claude plugin eval` run output |
| REQ-CKPT-03 | unit (shell) | Yes | `template-sensor-tests.sh` new cases (checkpoint present/absent, Tier 1, no sibling spec) | `plugins/evidence-sdlc/scripts/tests/template-sensor-tests.sh` | test script stdout, all `PASS` |
| REQ-EVAL-01 | manual — content review | No | — | `definition-of-ready-and-done.md` + `docs/extending.md` diff | PR review of both diffs |
| REQ-EVAL-02 | unit (shell) | Yes | `template-sensor-tests.sh` new cases (eval case present/absent for a new SKILL.md) | `plugins/evidence-sdlc/scripts/tests/template-sensor-tests.sh` | test script stdout, all `PASS` |

## Considered and rejected
- **A new dedicated gate script instead of extending `template-sensor.sh`.**
  Rejected: both new checks are advisory in nature (a missed checkpoint marker or a
  missing eval case is a quality signal, not a security or compliance control that
  should ever block a commit), and the existing sensor already has the exact
  file-reading/section-extraction machinery needed. A new script would duplicate that
  machinery for no behavioral difference. See spec.md's "Rejected alternatives" for
  the checkpoint-trigger and debt-signal design choices (wall-clock/session-boundary
  trigger; mandatory new debt-register file) — both rejected there before this plan
  was written.
- **Making the new Done-table row and eval cases hard requirements (● in all tiers)
  instead of conditional.** Rejected: "eval case exists" only makes sense when a new
  skill was introduced, exactly like the existing "ADR stored (if a design decision
  was made)" row — marking it unconditionally required would misfire on every
  ordinary Tier 2/3 change that touches no skill at all.
