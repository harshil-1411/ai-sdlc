# evidence-quality eval summary

Run: 2026-09-24T04:41:24.174Z, Claude Code 2.1.281, complete, 30 cases, cost $10.89. Scores are the mean over runs; Δ = with − without.
Skill-fired graders are an indicator only (they do not score the baseline arm).

v2 pass, 2 runs per arm, run against the plugin with the hard `dependencies` field removed (see CHANGELOG). Partial runs stopped at the per-plugin cost cap; uncovered cases were not scored in this pass.

| Case | With | Without | Δ | Skill fired (with) |
| --- | ---: | ---: | ---: | --- |
| accessibility-testing-automated-scan-is-not-enough | 1.00 | 1.00 | +0.00 | yes/yes |
| accessibility-testing-fires-on-wcag-question | 1.00 | 0.00 | +1.00 | yes/yes |
| accessibility-testing-no-fire-on-db-index | 1.00 | 1.00 | +0.00 | yes/yes |
| continuous-testing-blocks-vs-informs | 1.00 | 1.00 | +0.00 | yes/yes |
| continuous-testing-fires-on-pipeline-design | 0.50 | 0.50 | +0.00 | yes/yes |
| continuous-testing-no-fire-on-unit-test-request | 1.00 | 1.00 | +0.00 | yes/yes |
| e2e-ui-testing-does-not-assume-a-tool | 1.00 | 1.00 | +0.00 | yes/yes |
| e2e-ui-testing-fires-on-playwright-request | 1.00 | 0.00 | +1.00 | yes/yes |
| e2e-ui-testing-no-fire-on-api-validation-test | 1.00 | 1.00 | +0.00 | yes/yes |
| performance-testing-fires-on-load-test-request | 1.00 | 0.00 | +1.00 | yes/yes |
| performance-testing-no-fire-on-unit-test-fix | 1.00 | 1.00 | +0.00 | yes/yes |
| performance-testing-refuses-to-invent-target | 1.00 | 1.00 | +0.00 | yes/yes |
| security-testing-fires-on-dast-request | 1.00 | 0.00 | +1.00 | yes/yes |
| security-testing-no-fire-on-copy-change | 1.00 | 1.00 | +0.00 | yes/yes |
| security-testing-suppression-needs-owner-and-expiry | 1.00 | 0.00 | +1.00 | yes/yes |
| static-analysis-fires-on-lint-baseline-request | 1.00 | 0.00 | +1.00 | yes/yes |
| static-analysis-no-fire-on-date-parsing | 1.00 | 1.00 | +0.00 | yes/yes |
| static-analysis-refuses-to-disable-rule-to-pass | 1.00 | 0.50 | +0.50 | yes/yes |
| test-automation-fires-on-flaky-test | 1.00 | 1.00 | +0.00 | no/no |
| test-automation-no-fire-on-unrelated-summary | 1.00 | 1.00 | +0.00 | yes/yes |
| test-automation-tags-for-traceability | 0.50 | 0.67 | -0.17 | yes/yes |
| test-strategy-fires-on-spec-review | 1.00 | 0.00 | +1.00 | yes/yes |
| test-strategy-no-fire-on-factual-stack-question | 1.00 | 1.00 | +0.00 | yes/yes |
| test-strategy-tier3-manual-attestation | 0.50 | 1.00 | -0.50 | no/no |
| testrail-authoring-fires-with-recorded-write-access | 0.67 | 0.67 | +0.00 | yes/yes |
| testrail-authoring-no-fire-on-ci-status-question | 1.00 | 1.00 | +0.00 | yes/yes |
| testrail-authoring-stops-without-recorded-write-decision | 0.50 | 1.00 | -0.50 | no/no |
| traceability-ids-cross-repo-single-parent-key | 1.00 | 0.00 | +1.00 | yes/yes |
| traceability-ids-fires-on-new-branch-request | 1.00 | 0.50 | +0.50 | yes/yes |
| traceability-ids-no-fire-on-pure-formatting-request | 1.00 | 1.00 | +0.00 | yes/yes |

**Discrimination:** plugin beats baseline on 10 case(s), ties on 17, loses on 3. Mean Δ +0.26. Skill fired on every run in 27 of 30 trigger-graded case(s).
