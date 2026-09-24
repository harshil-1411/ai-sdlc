# evidence-discovery eval summary

Run: 2026-09-24T04:49:55.652Z, Claude Code 2.1.281, PARTIAL (cost_ceiling), 19 cases, cost $7.22. Scores are the mean over runs; Δ = with − without.
Skill-fired graders are an indicator only (they do not score the baseline arm).

v2 pass, 2 runs per arm, run against the plugin with the hard `dependencies` field removed (see CHANGELOG). Partial runs stopped at the per-plugin cost cap; uncovered cases were not scored in this pass.

| Case | With | Without | Δ | Skill fired (with) |
| --- | ---: | ---: | ---: | --- |
| compliance-discovery-fires-on-regulation-question | 1.00 | 0.00 | +1.00 | yes/yes |
| compliance-discovery-no-fire-on-favicon-request | 1.00 | 1.00 | +0.00 | yes/yes |
| compliance-discovery-pushes-back-on-casual-none-apply | 1.00 | 1.00 | +0.00 | yes/yes |
| design-system-discovery-fires-on-component-question | 1.00 | 0.00 | +1.00 | yes/yes |
| design-system-discovery-flags-duplicate-libraries-as-ask | 1.00 | 0.50 | +0.50 | yes/yes |
| design-system-discovery-no-fire-on-unrelated-script | 1.00 | 1.00 | +0.00 | yes/yes |
| document-ingestion-fires-on-legacy-sop-migration | 1.00 | 1.00 | +0.00 | yes/yes |
| document-ingestion-no-fire-on-markdown-formatting | 1.00 | 1.00 | +0.00 | yes/yes |
| document-ingestion-refuses-retype-shortcut | 1.00 | 0.00 | +1.00 | no/no |
| stack-discovery-favors-code-over-docs | 1.00 | 0.00 | +1.00 | yes/no |
| stack-discovery-fires-on-stack-question | 1.00 | 0.50 | +0.50 | yes/yes |
| stack-discovery-flags-ambiguous-stack-as-ask | 1.00 | 0.00 | +1.00 | yes/yes |
| stack-discovery-no-fire-on-unrelated-edit | 1.00 | 1.00 | +0.00 | yes/yes |
| test-strategy-discovery-fires-on-onboarding-question | 1.00 | 0.00 | +1.00 | yes/yes |
| test-strategy-discovery-no-fire-on-assertion-error | 1.00 | 1.00 | +0.00 | yes/yes |
| test-strategy-discovery-out-of-scope-needs-decider | 1.00 | 0.00 | +1.00 | yes/yes |
| toolchain-discovery-fires-on-connectivity-question | 1.00 | 0.00 | +1.00 | yes/yes |
| toolchain-discovery-flags-community-mcp-risk | 0.00 | 0.00 | +0.00 | no/no |
| toolchain-discovery-no-fire-on-unrelated-refactor | 1.00 | 1.00 | +0.00 | yes/yes |

**Discrimination:** plugin beats baseline on 10 case(s), ties on 9, loses on 0. Mean Δ +0.47. Skill fired on every run in 16 of 19 trigger-graded case(s).
