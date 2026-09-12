# Plan: Regression tests for the gate scripts
Tracker: TRACE-1   From: spec.md   Approved by: suparn.bector@msbdocs.com (maintainer)   Date: 2026-09-12

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Files that change

- `plugins/evidence-sdlc/scripts/tests/gate-regression-tests.sh` (new — directory
  already created and verified to exist)
- `validation/traceability.csv` (new — the sample export this whole exercise exists
  to produce; directory created in this same change)

## Order of work

1. Write `gate-regression-tests.sh`: for each of the six gate scripts, define its
   true-positive and false-positive cases as data (name, target script, JSON stdin
   payload, expected outcome — `deny` or `allow`), then a runner loop that feeds each
   payload to the real script via `echo '<json>' | bash <script>.sh`, checks the
   output for `"permissionDecision": "deny"`, compares against the expected outcome,
   and tracks pass/fail counts. Exit non-zero if any case fails.
2. Run it against the current (fixed) scripts. Confirm every case passes — this is
   REQ-GATE-01 and REQ-GATE-02's acceptance criterion.
3. Prove the suite discriminates (REQ-GATE-03): temporarily revert one script to its
   pre-fix state (via `git show <commit>~1:<path>`, not by hand-editing), re-run the
   suite, confirm the corresponding case(s) now FAIL and the suite exits non-zero,
   then restore the fixed version and re-confirm a clean pass. This step is
   independent of step 2 in the sense that it doesn't change the committed script —
   only the verification method.
4. Write `validation/traceability.csv` with one row per requirement (REQ-GATE-01,
   -02, -03), citing the actual spec commit SHA, the actual implementing commit SHA
   (from step 1-2), the test run's result, and Tier 1 / no revalidation.
5. Commit the test script and its passing run as one commit; commit the traceability
   export as a separate commit, since the export cites the test-script commit's SHA
   and so must come after it exists.

Steps 1-3 are sequential (each depends on the last). Step 4 depends on steps 1-3
having produced a real commit SHA and a real pass/fail result to cite — it cannot be
written first without inventing evidence, which `evidence-package`'s own rule
forbids ("Evidence is a link... never a description").

## Reuse decisions

No existing test tooling exists in this repository (`stack.md`: "Test frameworks and
locations: none present") — there is nothing to extend. The six gate scripts
themselves are reused as-is (invoked, not modified) by the new test script.

## Risks

- **The suite could pass vacuously** (e.g. a shell bug causes every case to report
  PASS regardless of actual outcome). Mitigated by REQ-GATE-03 / plan step 3:
  proving the suite fails against a known-bad prior version is the actual guard
  against this, not just running it once and reading "all green."
- **Branch-name dependency**: the `block-protected-branch-push.sh` true-positive case
  only denies when run from a protected branch name. This repo's current branch is
  `master` (protected per that script's own list), confirmed via
  `git rev-parse --abbrev-ref HEAD` in-session, so the case is real, not skipped —
  but if this suite is ever run from a feature branch, that one case would need
  `[[ NEEDS VERIFICATION ]]`-level attention (it would show as unexpectedly passing
  the false case rather than exercising the true one). Documented in the test
  script's own comments so a future maintainer sees this immediately.
- Rollback: deleting the new script and the new CSV fully reverts this change; it
  touches no other file.

## Proof
See the test plan section (from the `test-strategy` skill).

| REQ ID | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- |
| REQ-GATE-01 | Script / integration (shell invocation of the real gate scripts) | Yes | GATE-TP (true-positive set, one per script) | `plugins/evidence-sdlc/scripts/tests/gate-regression-tests.sh` | Test run output committed in the implementing commit message |
| REQ-GATE-02 | Script / integration | Yes | GATE-FP (false-positive set, PILOT-9..12) | `plugins/evidence-sdlc/scripts/tests/gate-regression-tests.sh` | Test run output committed in the implementing commit message |
| REQ-GATE-03 | Script / integration (discrimination check) | Yes | GATE-DISCRIMINATE | `plugins/evidence-sdlc/scripts/tests/gate-regression-tests.sh` run against a reverted script | Before/after run output committed in the implementing commit message |

## Considered and rejected

- A single monolithic test per script instead of per-case: rejected, because a single
  pass/fail per script would hide exactly the kind of partial regression (one case
  breaks, others still pass) that PILOT-9 through PILOT-12 individually were.
- Testing via the actual Claude Code hook runtime (triggering real tool calls) instead
  of direct script invocation: rejected as impractical for a repeatable, CI-runnable
  suite — the six scripts already take their input as JSON on stdin specifically so
  they can be invoked this way directly, and that is what this repo's own maintainers
  did by hand to verify PILOT-9 through PILOT-12; the suite formalizes that exact
  method.
