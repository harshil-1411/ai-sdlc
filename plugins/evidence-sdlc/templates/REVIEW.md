# Review instructions (the organisation)

## Passes
Run four passes and tag each finding with its pass:

- **Bugs** — logic errors, broken edge cases, subtle regressions, concurrency.
- **Security** — tenant isolation, object-level authorization, authentication,
  injection, secrets, PII in logs, supply chain. Apply the secure-api-review skill.
- **Compliance** — the control sets that actually apply to this project, and evidence
  impact. Apply the regulatory-controls and evidence-package skills; they read
  .evidence/context/compliance.md. Mandatory when the diff touches audit, authentication,
  authorisation, retention, export, personal or sensitive data, or a regulated workflow.
- **Conformance** — does the diff match spec.md and plan.md? Flag silent drift and
  any requirement ID with no covering test.

## What Important means here
Reserve Important for findings that would break behaviour, leak or cross-contaminate
tenant data, compromise signature or audit integrity, or breach a regulatory control.
Style and naming are nits.

## Cap the nits
At most five nits per review; summarize the rest as a count.

## Do not report
Generated files, vendored code, and anything CI already enforces.

## Human threshold
Findings inform; they do not approve or block on their own. Branch protection still
requires a code owner. Any Compliance or Critical/High Security finding additionally
requires the named framework owner from the compliance profile, or the Security owner,
before merge.
