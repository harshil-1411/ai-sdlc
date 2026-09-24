---
name: static-analysis
description: Configure and maintain static code analysis — linting, formatting, type checking, complexity and duplication checks, and SAST rule sets — with a baseline-and-ratchet policy so new code is clean while existing debt shrinks, and with suppression and rule-change discipline. Use this whenever someone sets up or changes a linter, formatter, type checker, SonarQube/Semgrep/CodeQL or similar configuration, asks to introduce static analysis to an existing codebase, wants to disable, relax or ignore a rule, adds a lint/eslint/noqa/nolint suppression, or asks why a static check is failing. Read the tools and their commands from the repository profile — never assume them.
---

# Static analysis

Read `.evidence/context/stack.md` for the linters, formatters, type checkers and
analysers this repository actually runs, and `test-strategy.md` for where the
baseline lives and which categories are in scope. Security findings produced by SAST
are triaged under `security-testing`'s findings policy. This skill owns how the tools
are configured and how the rules change.

## Categories and where each runs

| Category | Catches | Runs | Blocks? |
| --- | --- | --- | --- |
| **Formatting** | Style churn in diffs | Pre-commit (auto-fix) + commit | Yes, cheaply: auto-fix, don't argue |
| **Linting** | Likely bugs, unused code, unsafe patterns, framework misuse | Pre-commit on changed files + commit | Errors yes, warnings inform |
| **Type checking** | Type errors, nullability, contract drift between modules | Commit | Yes |
| **Complexity / duplication** | Functions too complex to test well, copy-paste | PR | Informs reviewer |
| **SAST** | Injection, unsafe deserialisation, crypto misuse, taint flows | Commit (fast rules) + nightly (deep rules) | New high/critical: yes (see `security-testing`) |

The cheapest check runs at the earliest stage (`continuous-testing`). Fast rules
belong in the commit stage. Whole-program analysis that takes twenty minutes belongs
in nightly runs.

## Introducing analysis to an existing codebase: baseline and ratchet

Turning on a strict rule set over old code produces thousands of findings. Teams
then either ignore the tool or disable it. Instead:

1. **Record a baseline** of existing findings in the tool's own baseline mechanism,
   committed to the repository at the location recorded in `test-strategy.md`.
2. **Block only on new findings** in new or changed code.
3. **Ratchet.** The baseline may only shrink. A change that grows it is a finding.
   When code in the baseline is touched, fix its findings in that area, or record why not.
4. **Track baseline size** as a metric over time, alongside flake rate and commit-stage
   duration.

## Suppressions

An inline suppression (`eslint-disable`, `# noqa`, `//nolint`, `@SuppressWarnings`,
`# nosec` and similar) is allowed only when:
- it names the **specific rule**, never a blanket disable of all rules for a line or file
- it carries an **inline reason** a reviewer can check ("false positive: value is
  a compile-time constant, see <link>")
- it is scoped to the smallest region possible
- for a security rule, it meets `security-testing`'s suppression policy, which
  also requires an owner, an approver and an expiry

Suppressions are counted and reported like the baseline. A rising suppression
count is the same failure as a rising baseline.

## Rule-set changes are their own change

Enabling, disabling or relaxing a rule, or changing a threshold, is a **separate
reviewed change**. It has its own reason and does not go in a feature diff. A rule turned
off inside the same PR that would otherwise fail it is the static-analysis equivalent
of deleting a failing test. The `block-test-weakening` spirit applies.

## When a static check fails

1. Read the finding and decide: is it a real defect, a false positive, or a rule that
   does not fit this codebase?
2. A real defect gets fixed.
3. A false positive gets a narrow, reasoned suppression.
4. A rule that does not fit gets a **separate** rule-change proposal. The current PR
   still passes on its own merits.

Never make the check pass by disabling the rule, widening an ignore pattern, moving
code into an excluded path, or lowering a threshold inside the change that fails it.

## Evidence

Per commit or PR stage: tool and version, rule-set version, a report of new findings
on changed code, baseline size before and after, and suppressions added in this
change with their reasons. Link from the tracker key.

## Never

- Never disable, relax or exclude a rule to make a failing change pass.
- Never add a blanket or reasonless suppression.
- Never let the baseline grow silently.
- Never gate on a total finding count across the repository. Gate on new findings.
- Never introduce a new analyser or rule set without a plan. That is a change to what
  blocks merges.
