---
name: root-cause-analysis
description: Trace a defect to its actual root cause from evidence, rather than proposing a plausible-sounding fix. Use this whenever someone says "this is broken", "why is this failing", "debug this", "investigate this error", "production issue", "it works locally but not in X", pastes a stack trace or error log, or reports any unexpected behaviour. Refuse to theorise until the essential facts are established or explicitly marked unavailable.
---

# Root cause analysis

Bug-fix work is a large share of real engineering time, and it is where an agent is
most tempted to skip straight to a plausible-looking fix. This skill exists to stop
that: a plausible explanation is not a root cause, and a fix for the wrong cause is a
fix that will recur.

## Intake — refuse to theorise until you have this

Before proposing any explanation, establish, or explicitly mark as unavailable:

- The code path involved
- Expected behaviour
- Actual behaviour
- Logs, errors, stack traces
- Reproduction steps
- When it started, and what changed around then

Ask only for what is essential and missing — apply the same bar as
`stack-discovery`'s "ask only for what is essential and missing" rule: something you
could establish by reading the code or the logs yourself is not a question. Do not
interrogate; ask for the smallest set of missing facts in one round.

## Rule — do not guess

Trace the issue to its actual root cause. A plausible explanation is not a root
cause. If you cannot establish the cause from available evidence, say which evidence
would settle it rather than proposing a fix that might work.

## Rule — state your assumptions

Before proposing anything, list every assumption you are making, explicitly, as a
list. An assumption that turns out wrong should be visible as one line a reviewer can
challenge, not buried in prose.

## Reproduce before fixing

Write a failing test that demonstrates the bug, and confirm it fails **for the
expected reason** — step through why it fails and check that reason matches the bug,
not an unrelated setup error or a typo in the test itself. Commit that test on its
own, before any fix. Then set `FIX_TASK=1` for the rest of the session — from that
point the `block-test-weakening` hook denies edits to that test, so the fix has to
make the test pass rather than the test being loosened to fit whatever the fix does.

## Root cause vs. trigger

The trigger is the specific input, timing, or event that made the defect surface. The
root cause is the underlying condition that made it possible at all. Report both —
fixing only the trigger (e.g. rejecting the one input that happened to expose it)
without fixing the root cause leaves the same defect reachable a different way.

## Regulated records

If the defect touched a regulated record, say so immediately and point at
`governance/deviation-capa-runbook.md`. Classification is by impact — what the defect
touched and what it could have affected — not by who or what authored the change that
introduced it, and not by whether it was caught before release.

## Output format

Report the finding as a table:

| Symptom | Trigger | Root cause | Evidence for that conclusion | Assumptions | Edge cases this also affects | Proposed fix | Test that proves it |
| --- | --- | --- | --- | --- | --- | --- | --- |
