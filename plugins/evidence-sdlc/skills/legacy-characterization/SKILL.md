---
name: legacy-characterization
description: Write characterization tests that pin down what existing untested code actually does before anything changes it, choosing modules by churn, incident history and the team's fear list. Use before modifying a thinly tested module, before a refactor or framework upgrade, when someone calls code scary, risky, legacy or not understood, and when onboarding an old repository.
---

# Legacy characterization

In most organisations, engineering time is dominated by code that predates every
process in this framework and has thin coverage. Agents change such code confidently and wrongly.
Characterization tests are the cheapest way to make everything downstream safe, and
they are the highest-value early use of an agent — higher than feature work.

## What a characterization test is

It captures **what the code currently does**, not what it should do. If current
behaviour is wrong, the test still records it — with a comment saying so. You are
building a tripwire, not a specification.

## Procedure

1. **Rank candidates by fear, churn and incidents — not by coverage percentage.**
   Combine three signals:
   - **Fear list** — ask the team which files they avoid touching.
   - **Churn** — files changed most often in the last year:
     `git log --since=12.months --format= --name-only | sort | uniq -c | sort -rn | head -30`
   - **Incident signal** — files most often touched by fixes:
     `git log --since=12.months -i --grep=fix --grep=bug --grep=hotfix --format= --name-only | sort | uniq -c | sort -rn | head -30`,
     plus files named in incident or postmortem records if the tracker is reachable.

   Rank files that appear on two or more lists first. Present the ranked list with the
   counts behind each entry and let the team confirm the order. That list is the backlog.
2. **Map it first** with the `codebase-cartographer` agent: entry points, callers,
   side effects, external dependencies, data it reads and writes.
3. **Enumerate observable behaviour.** For each entry point: inputs, outputs, thrown
   exceptions, database writes, emitted events, audit records, log lines that something
   downstream parses.
4. **Write tests that assert current behaviour**, including the behaviour that looks
   like a bug. Mark those: `// CHARACTERIZATION: current behaviour, believed incorrect
   — see <ticket>. Do not "fix" without a spec.`
5. **Run them against unmodified code.** Every one must pass. A failing characterization
   test means you misunderstood the code — fix your understanding, not the code.
6. **Commit them separately**, before any behavioural change, in their own PR. This is
   important: it makes the tripwire independently reviewable and gives you a clean
   before/after.
7. **Then** make the intended change. Any characterization test that now fails is a
   behaviour change — either intended (update the test, in the same commit, with a
   reason) or a regression (stop).

## For regulated modules

Characterize the audit trail explicitly: for each operation, which audit events fire,
in what order, with which fields. Audit-trail regressions are silent, are Critical under
the deviation runbook, and are exactly what this catches.

## Rules

- Do not refactor while characterizing. Two changes at once and you cannot tell which
  broke it.
- Do not delete a characterization test to make a change pass. Once a `fix` change
  passes its `failing-test` stage the engine denies edits to pre-existing tests; do not
  route around it.
- Coverage percentage is not the goal. Covering the paths people are afraid of is.
