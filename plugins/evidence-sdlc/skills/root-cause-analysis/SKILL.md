---
name: root-cause-analysis
description: Trace a defect to its root cause from evidence — reproduction, git history and bisect, a causal chain, and a sweep for the same defect elsewhere — instead of a plausible fix. Use when someone says "this is broken", "why is this failing", "debug this", "production issue", "it works locally but not in X", pastes a stack trace or error log, or reports unexpected behaviour. Refuse to theorise until the facts are established.
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

1. Start the fix as a change: `evidence change start <KEY> --tier <n> --kind fix`
   (apply `risk-tiering` for the tier).
2. Write a failing test that demonstrates the bug, and confirm it fails **for the
   expected reason** — step through why it fails and check that reason matches the bug,
   not an unrelated setup error or a typo in the test itself.
3. Commit that test on its own, before any fix, then run
   `evidence change advance <KEY> failing-test`. From then on the engine denies edits to
   and deletion of every test file that existed before the fix, so the fix has to make
   the test pass rather than a test being loosened to fit whatever the fix does. New test
   files are still allowed. (`FIX_TASK=1` is deprecated; it is still honoured but does
   not replace the change record.)

## Find when and how it entered

Use history before theory:

- `git log -S '<suspect string>' --oneline -- <path>` and `git log -L <start>,<end>:<file>`
  to find the commits that introduced or changed the suspect code.
- If a known-good commit exists, bisect with the failing test:
  `git bisect start <bad> <good>` then `git bisect run <command that runs only the
  failing test>`, and `git bisect reset` when done. Report the first bad commit and
  read its diff and message — the intent behind it is often the root cause.
- If bisect is impossible (no good commit, test cannot run on old revisions), say so
  and why.

## Causal chain

The trigger is the specific input, timing, or event that made the defect surface. The
root cause is the underlying condition that made it possible at all. Write the chain
explicitly, one link per line, each with its evidence:

`Trigger → Mechanism (each step the fault propagated through) → Root cause`

Stop the chain where a change would prevent the whole class of failure, not just this
instance. Fixing only the trigger (e.g. rejecting the one input that happened to expose
it) leaves the same defect reachable a different way.

## Sibling-defect sweep

A root cause is a pattern, and patterns repeat. Before proposing the fix, search for the
same pattern elsewhere — grep for the faulty call, the missing check, the copied block,
the same misuse of an API. List every sibling found with its path and whether it is
reachable. Fix siblings in this change only if the plan claims them; otherwise raise
each as its own tracker issue.

## Regulated records

If the defect touched a regulated record, say so immediately and point at
`governance/deviation-capa-runbook.md`. Classification is by impact — what the defect
touched and what it could have affected — not by who or what authored the change that
introduced it, and not by whether it was caught before release.

## Output format

Report the finding as a table:

| Symptom | Trigger | Root cause | Introducing commit | Evidence for that conclusion | Assumptions | Sibling defects | Proposed fix | Test that proves it |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

Follow the table with the causal chain.
