# Examples

Two kinds of thing live here, for two different reasons:

- **`scenarios/`** — worked walkthroughs showing this framework applied to a real
  kind of change end to end: which skill fires, what artifact it produces, which
  gate checks it, and why. Read these to see the framework in motion rather than
  reconstructing it from the skill files in the abstract.
- **`skills/`** — skills that are **not installed by default**. They live outside
  `plugins/`, so no plugin manifest loads them and they do not appear in an installed
  session's skill list. Every added skill dilutes the trigger space of the others
  (see the main README), so a skill moves here rather than being deleted when its use
  is real but occasional enough that most repositories shouldn't pay its
  trigger-space cost by default.

## scenarios/ — ten worked examples

| Scenario | What it shows |
| --- | --- |
| [`new-feature-non-regulated`](scenarios/new-feature-non-regulated/README.md) | The lightest path: a Tier 1 user story in a product with no regulatory obligation |
| [`regulated-change-tier3`](scenarios/regulated-change-tier3/README.md) | The heaviest path: adding electronic signature capture under 21 CFR Part 11 |
| [`v2-gates-in-action`](scenarios/v2-gates-in-action/README.md) | A Tier 3 auth change hitting each v2 gate: editing before approval, human approval by plan hash, an edit outside the claims, a Bash write, push before the review agents, and an attempt to set `RELEASE_APPROVAL` through settings. Each step shows the real deny message |
| [`incident-bug-fix`](scenarios/incident-bug-fix/README.md) | Root cause before fix, a failing test committed first and locked with `evidence change advance KEY failing-test`, and why the entry point isn't Plan |
| [`schema-migration-regulated-table`](scenarios/schema-migration-regulated-table/README.md) | Expand-contract phasing and the regulated-record checks a normal migration skips |
| [`third-party-integration`](scenarios/third-party-integration/README.md) | Calling an external e-signature API — where security review ends and integration review begins |
| [`standalone-cli-audit`](scenarios/standalone-cli-audit/README.md) | Using just `cli/evidence` on a repository that doesn't use this framework, or any framework, at all |
| [`qa-evidence-profile`](scenarios/qa-evidence-profile/README.md) | The evidence profile and per-layer test-case design made concrete: what `test-designer` actually produces for one regulated requirement, and where each case's evidence lands |
| [`test-strategy-and-release-cycle`](scenarios/test-strategy-and-release-cycle/README.md) | The testing side end to end: the onboarding test-strategy interview, one change's performance, accessibility, E2E and security requirements planned and proven, the rules that stop the usual shortcuts, and a test summary report with a human-signed go/no-go |
| [`sensor-and-learning-loop`](scenarios/sensor-and-learning-loop/README.md) | Two advisory-only mechanisms working together: the sensor that catches an unfilled spec section, and the learning loop that turns a mid-session correction into a durable `CLAUDE.md` rule |

## skills/decision-council

Multi-perspective pressure test for a consequential, hard-to-reverse decision. Moved
here from `plugins/evidence-sdlc/skills/` because it is expensive and occasional by
design (`decision-council`'s own text: "Do not convene for... a decision that is
cheap to undo") — most sessions should not have its trigger phrases ("council this",
"pressure-test this") competing for attention on every design conversation.

To use it in a repository: copy `examples/skills/decision-council/` into
`plugins/evidence-sdlc/skills/decision-council/` (or your own plugin's `skills/`
directory) in your fork. It has no dependency on being inside `evidence-sdlc`
specifically — it only references `regulatory-controls` and `secure-api-review` by
name, both of which any installation running it would also have.
