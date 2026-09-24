# evidence-integrations eval summary

Run: 2026-09-24T04:55:57.468Z, Claude Code 2.1.281, complete, 9 cases, cost $2.95. Scores are the mean over runs; Δ = with − without.
Skill-fired graders are an indicator only (they do not score the baseline arm).

v2 pass, 2 runs per arm (with the plugin vs a clean baseline; the user-scope install was disabled for the run).

| Case | With | Without | Δ | Skill fired (with) |
| --- | ---: | ---: | ---: | --- |
| contract-testing-fires-on-new-integration | 1.00 | 0.50 | +0.50 | yes/yes |
| contract-testing-no-fire-on-internal-util | 1.00 | 1.00 | +0.00 | yes/yes |
| contract-testing-refuses-to-patch-contract-to-pass | 1.00 | 1.00 | +0.00 | yes/yes |
| contract-testing-rejects-sandbox-suite-as-only-proof | 1.00 | 1.00 | +0.00 | yes/yes |
| integration-change-deprecation-is-its-own-change | 1.00 | 0.00 | +1.00 | yes/yes |
| integration-change-fires-on-new-external-call | 0.50 | 0.00 | +0.50 | yes/yes |
| integration-change-flags-regulated-record-crossing | 1.00 | 0.00 | +1.00 | yes/yes |
| integration-change-flags-webhook-idempotency-and-signature | 1.00 | 1.00 | +0.00 | yes/yes |
| integration-change-no-fire-on-internal-refactor | 1.00 | 1.00 | +0.00 | yes/yes |

**Discrimination:** plugin beats baseline on 4 case(s), ties on 5, loses on 0. Mean Δ +0.33. Skill fired on every run in 9 of 9 trigger-graded case(s).
