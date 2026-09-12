# Spec: Regression tests for the gate scripts
Tracker: TRACE-1   From: intent/2026-09-12-gate-regression-tests/intent.md   Risk tier: 1

Tier 1 — Routine, stated per risk-tiering before any design below: this is a test
addition to internal tooling, fully within this session's own verification of
PILOT-9 through PILOT-12, touching no regulated record and no production code path.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Requirements
| ID | Requirement | Source (intent.md section) | Acceptance |
| --- | --- | --- | --- |
| REQ-GATE-01 | The regression suite denies every documented true-positive case across the six gate scripts fixed in this pilot round (gate-plan-exists.sh, production-gate.sh, block-test-weakening.sh, protect-validated-paths.sh, require-issue-key.sh, block-protected-branch-push.sh). | Problem | Running the suite exits 0 and reports every true-positive case as PASS when run against the current (fixed) scripts. |
| REQ-GATE-02 | The regression suite allows every documented false-positive case that PILOT-9 through PILOT-12 fixed (the ones that previously false-triggered). | Problem | Running the suite exits 0 and reports every false-positive case as PASS when run against the current (fixed) scripts. |
| REQ-GATE-03 | The regression suite actually discriminates — it must fail if a fix is reverted, not just pass unconditionally. | Proposed outcome | Running the suite against a deliberately reverted copy of one fixed script reports that case as FAIL and the suite exits non-zero. |

## Design
One new script, `plugins/evidence-sdlc/scripts/tests/gate-regression-tests.sh`. It
defines, per gate script, the true-positive and false-positive cases already verified
by hand in the PILOT-9 through PILOT-12 commit messages, feeds each as JSON on stdin
to the real script (the same invocation shape the Claude Code hook runtime uses:
`echo '<json>' | bash <script>.sh`), and asserts the expected outcome (deny vs.
allow) by checking for `"permissionDecision": "deny"` in the output. No existing
module is extended or duplicated — there is no existing test tooling in this
repository to extend (`.evidence/context/stack.md`: "Test frameworks and locations:
none present").

## Regulatory control impact
`.evidence/context/compliance.md` has no confirmed applicable framework — every row is
`[ASK]`, and the file's own Step 4 logic ("the 'none apply' case is a real answer")
applies here: this change touches no regulated record and no data of any class, so no
control-set reference is loaded.

| Framework | Control ID | Applies? | How it is satisfied | Evidence |
| --- | --- | --- | --- | --- |
| N/A | N/A | No | No framework is confirmed applicable to this repository's own governance (compliance.md, all rows [ASK]), and this change touches no regulated record regardless. | intent.md "Regulated record impact" |

## Evidence impact
New requirement entries REQ-GATE-01, REQ-GATE-02, REQ-GATE-03 are added (nothing
retired or modified — no prior traceability rows existed for this repository's own
changes before TRACE-1). Re-verification: none — Tier 1, no revalidation obligation
exists for this repository (no confirmed compliance framework).

## Diagrams
None needed. A single test script invoking six existing gate scripts with synthetic
stdin input has no new module boundary, sequence, state machine, data flow, or
deployment topology to depict.

## Security design
N/A. No new endpoint, no new trust boundary, no authorization change, no new
dependency, no third-party call. The test suite reads only files already in this
repository and writes only its own output to stdout/exit code.

## UX
<Delete rows that do not apply; do not delete the table.>

| State / concern | Behaviour |
| --- | --- |
| N/A | This change has no UI — it is an internal shell test script with no user-facing surface. |

Component reuse: N/A — no design system applies to a repository with no application UI.

## Areas of concern
- **Tracker-key convention.** `TRACE-1` (like the earlier `PILOT-<n>`/`TASK2-<item>`
  tags) is a session-local convention set via `EVIDENCE_ISSUE_KEY_PATTERN` in
  `.claude/settings.json`, not a real tracker. `.evidence/context/stack.md` already
  logs this as an open `[ASK]` ("no branch naming, commit message, or issue-key
  pattern exists yet for this repo's own history"). Owner: maintainer. This spec does
  not resolve it, only continues using the already-approved interim convention.
- **Whether this regression suite should be wired into CI** is a separate, broader
  question logged as its own `[ASK]` in `stack.md` and explicitly out of scope for
  this change (see intent.md). Owner: maintainer.

## Rejected alternatives
Considered adopting a real shell-testing framework (e.g. bats-core) instead of plain
`bash` assertions. Rejected: this repository has no package manager and no lockfile
concept (`stack.md`: "No `package.json`... found anywhere in the tree"); adding a
testing framework dependency here would be the first dependency this repository has
ever had, which is a bigger decision than a Tier 1 test-tooling change should make
unilaterally. Plain bash, using only `jq`, `python3` and `bash` builtins already
required by the gate scripts themselves, keeps this change dependency-free and
consistent with "no skill in this framework hardcodes a stack."
