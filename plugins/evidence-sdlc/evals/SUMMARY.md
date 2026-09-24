# evidence-sdlc eval summary

Run: 2026-09-24T04:24:55.636Z, Claude Code 2.1.281, PARTIAL (cost_ceiling), 34 cases, cost $17.43. Scores are the mean over runs; Δ = with − without.
Skill-fired graders are an indicator only (they do not score the baseline arm).

v2 pass, 2 runs per arm, run against the plugin with the hard `dependencies` field removed (see CHANGELOG). Partial runs stopped at the per-plugin cost cap; uncovered cases were not scored in this pass.

| Case | With | Without | Δ | Skill fired (with) |
| --- | ---: | ---: | ---: | --- |
| agent-trust-boundaries-fires-on-webhook-ingestion | 1.00 | 1.00 | +0.00 | yes/yes |
| agent-trust-boundaries-flags-agent-with-write-tool-as-critical | 1.00 | 1.00 | +0.00 | yes/yes |
| agent-trust-boundaries-no-fire-on-internal-trusted-batch-job | 1.00 | 1.00 | +0.00 | yes/yes |
| architect-flags-conflict-with-accepted-adr | 0.50 | 0.50 | +0.00 | yes/yes |
| code-reviewer-dispatch-on-tier3-prepush | 1.00 | 1.00 | +0.00 | — |
| codebase-grounded-planning-fires-with-profile-and-spec | 0.50 | 0.00 | +0.50 | yes/yes |
| codebase-grounded-planning-no-fire-on-pure-explanation | 1.00 | 1.00 | +0.00 | yes/yes |
| codebase-grounded-planning-refuses-to-self-approve | 1.00 | 0.00 | +1.00 | yes/yes |
| codebase-grounded-planning-stops-without-stack-profile | 1.00 | 0.00 | +1.00 | yes/yes |
| codebase-grounded-planning-writes-checkpoint-for-tier2 | 0.33 | 0.00 | +0.33 | yes/yes |
| docs-writer-dispatch-on-flag-rename | 1.00 | 1.00 | +0.00 | — |
| intent-capture-does-not-design-solution | 1.00 | 0.50 | +0.50 | yes/yes |
| intent-capture-handles-declined-answer | 1.00 | 1.00 | +0.00 | yes/yes |
| intent-capture-no-fire-on-status-query | 1.00 | 1.00 | +0.00 | yes/yes |
| intent-capture-triggers-on-raw-request | 1.00 | 0.00 | +1.00 | yes/yes |
| intent-capture-writes-intent-file | 0.50 | 0.00 | +0.50 | yes/yes |
| legacy-characterization-fires-on-scary-legacy-module | 1.00 | 1.00 | +0.00 | yes/yes |
| legacy-characterization-no-fire-on-new-well-tested-code | 1.00 | 1.00 | +0.00 | yes/yes |
| legacy-characterization-ranks-by-churn-and-fixes | 1.00 | 0.00 | +1.00 | yes/yes |
| release-manager-dispatch-on-readiness-check | 1.00 | 1.00 | +0.00 | — |
| release-readiness-fires-on-go-no-go | 1.00 | 0.00 | +1.00 | yes/yes |
| release-readiness-leaves-decision-blank | 1.00 | 1.00 | +0.00 | yes/yes |
| release-readiness-no-fire-on-release-date-helper | 1.00 | 1.00 | +0.00 | yes/yes |
| risk-tiering-classifies-regulated-change-as-tier3 | 1.00 | 0.50 | +0.50 | yes/yes |
| risk-tiering-debt-raises-tier | 1.00 | 0.00 | +1.00 | yes/yes |
| risk-tiering-fires-on-process-question | 1.00 | 0.00 | +1.00 | yes/yes |
| risk-tiering-no-fire-on-doc-typo-fix | 1.00 | 1.00 | +0.00 | yes/yes |
| root-cause-analysis-fires-on-bug-report | 1.00 | 1.00 | +0.00 | yes/yes |
| root-cause-analysis-fix-flow-locks-failing-test | 0.00 | 0.00 | +0.00 | no/yes |
| root-cause-analysis-no-fire-on-feature-request | 1.00 | 1.00 | +0.00 | yes/yes |
| root-cause-analysis-refuses-to-guess-without-repro | 1.00 | 1.00 | +0.00 | yes/yes |
| schema-migration-fires-on-migration-request | 0.50 | 0.00 | +0.50 | yes/yes |
| schema-migration-no-fire-on-unrelated-test-request | 1.00 | 1.00 | +0.00 | yes/yes |
| schema-migration-rejects-combined-add-and-remove | 0.00 | 0.00 | +0.00 | yes/yes |

**Discrimination:** plugin beats baseline on 13 case(s), ties on 21, loses on 0. Mean Δ +0.29. Skill fired on every run in 30 of 31 trigger-graded case(s).
