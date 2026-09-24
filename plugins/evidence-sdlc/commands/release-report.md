---
description: Draft the release readiness report and test summary for a change or release candidate
argument-hint: [KEY or release name]
---
Apply the release-readiness skill for: $ARGUMENTS

Dispatch the release-manager agent, then draft the test summary report from
evidence-quality's `templates/test-summary-report.md` using only linked evidence
(`evidence gaps`, `evidence change status`, test run reports). Leave the go/no-go decision
blank for the named human. Never set or suggest a value for RELEASE_APPROVAL.
