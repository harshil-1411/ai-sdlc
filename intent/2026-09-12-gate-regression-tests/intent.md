# Intent: Regression tests for the gate scripts

Tracker: TRACE-1   Author: suparn.bector@msbdocs.com, maintainer   Date: 2026-09-12   Status: accepted

## Problem

Between PILOT-9 and PILOT-12, four of this repository's own gate scripts
(`block-test-weakening.sh`, `protect-validated-paths.sh`, `require-issue-key.sh`,
`block-protected-branch-push.sh`) were found to have naive `case`/glob substring
matching that false-triggered on unrelated content — denying edits to ordinary files
like `latest_migration.py`, or denying benign commands that merely mentioned "git
push" inside a string. Two more (`gate-plan-exists.sh`, `production-gate.sh`) had the
same class of bug found and fixed earlier in the pilot round. Every one of these six
fixes was verified manually, by hand, in the session that made the fix — there is no
committed, repeatable test that would catch a regression if one of these patterns were
carelessly reintroduced later.

`.evidence/context/stack.md` already records this gap as an open `[ASK]`: "No CI
validation currently runs `bash -n` on the 10 shell scripts or JSON-parses the 11 JSON
files that CONTRIBUTING.md's contribution standard requires." This intent addresses
the narrower, more urgent slice of that gap — regression coverage for the specific
false-positive/true-positive behaviour of the six gate scripts already fixed — not the
broader CI question, which stays open pending the maintainer's answer.

This intent also serves a second purpose: it is the vehicle for producing a real,
non-empty sample traceability export (`validation/traceability.csv`) to show external
regulated QA/RA leads, per the precondition on Part B of the prompt-pattern rollout
(`plugins/evidence-sdlc/templates/decisions-log.md` and behavior-preserving-refactor,
performance-analysis, and related skills are on hold until that review happens). No
such export existed anywhere in this repository before this change — only the empty
`traceability-matrix.csv` template.

## Proposed outcome

A committed, runnable regression suite that feeds each gate script the known
false-positive and true-positive cases (the same ones verified by hand during
PILOT-9 through PILOT-12) and fails loudly if a future change to any of these scripts
reintroduces a false-positive or loses a true-positive. Exit code non-zero on any
failure, so it can be wired into CI later without rework.

## Affected users and systems

- Internal: anyone maintaining `plugins/evidence-sdlc/scripts/*.sh` or
  `plugins/evidence-quality/scripts/*.sh` in this repository.
- No customer-facing system, no consuming repository's runtime. This does not change
  what the gates do — it only adds a test that watches what they already do.

## Regulated record impact

No. This touches internal test tooling for the framework's own gate scripts. It does
not touch a signed or approved record, an audit trail, or a consent record. See
`.evidence/context/compliance.md` — the file has open `[ASK]` items about whether
evidence-chain *itself*, as a distributed product, carries any regulatory obligation,
but those questions are about the product's business/legal posture, not about whether
this specific internal test-tooling change touches a regulated record. It does not,
and that is a judgment call worth a compliance owner's confirmation if this pattern of
reasoning is going to be reused for future internal-tooling changes to this repo.

## Compliance evidence impact

No. This does not change any control this framework claims for *consuming*
repositories; it only adds test coverage for controls this repository already ships.

## Data classification

None. No data of any class is read, written, or transmitted by the test suite beyond
the shell scripts' own source and synthetic test-case strings already documented in
the PILOT-9 through PILOT-12 commit messages.

## Constraints

- Must run without network access or any credential (this repo has none configured).
- Must not depend on a real git repository state beyond what's already true here
  (current branch name, working tree) — the block-protected-branch-push.sh true-positive
  case specifically depends on running from a branch named `main`, `master`, `release`,
  `release/*` or `hotfix/*`; this repo's current branch (`master`) already satisfies
  that, so the test suite does not need to fabricate a branch.

## Out of scope

- The broader CI-automation question already logged as `[ASK]` in `stack.md`
  (whether `bash -n`/JSON-parse checks should run in CI) — unresolved, unrelated to
  the narrower regression-test goal here.
- Regression tests for `require-repo-profile.sh` and `check-test-plan-rows.sh` — the
  audit that preceded this intent found no bug in either (verified: `check-test-plan-rows.sh`'s
  `ls | head -1` usage doesn't check exit status, so the multi-glob quirk that bit
  `gate-plan-exists.sh` doesn't apply to it; `require-repo-profile.sh` has no
  command/path pattern-matching logic at all). Nothing to regress-test yet.

## Open questions

1. Should this regression suite be wired into an actual CI pipeline once one exists
   for this repo? — awaiting: maintainer (tracks the existing `[ASK]` in `stack.md`).
2. Is `PILOT-<n>`/`TRACE-<n>` an acceptable long-term tracker-key convention for
   changes made to evidence-chain's own repository, or should a real tracker be
   provisioned? — awaiting: maintainer (tracks the existing `[ASK]` in `stack.md`'s
   version-control-conventions section).
