---
name: legacy-characterization
description: Generate characterization tests that pin down what existing untested code actually does, before anything changes it. Use this before any modification to a module with thin test coverage, before any refactor or framework upgrade, whenever someone says a piece of code is scary, risky, legacy, or nobody understands it, and as the first workstream when onboarding an old repository into the AI-SDLC. Do this before features, not after.
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

1. **Pick the module by fear, not by coverage percentage.** Ask the team which files
   they avoid touching. That list is the backlog.
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
- Do not delete a characterization test to make a change pass. The
  `block-test-weakening` hook denies this during fix tasks; do not route around it.
- Coverage percentage is not the goal. Covering the paths people are afraid of is.
