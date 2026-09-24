# Intent: Testing depth across every test type, and a test-strategy interview at onboarding

Tracker: PILOT-51   Author: suparn.bector@msbdocs.com, engineering   Date: 2026-09-24   Status: accepted

## Problem
A review of how the plugins handle testing (this session, 2026-09-24) found that
the framework has a strong *spine* — every requirement must name a proving test,
the traceability chain, flake policy, contract testing, legacy characterization —
but uneven *depth* per test type, and no conversation with the adopting team about
what their testing strategy actually is:

1. **No test-strategy interview.** `evidence-discovery` establishes test frameworks
   and the test-management tool as facts, but nothing asks the team which test
   types are in scope, what the non-functional targets are, which environments and
   browsers matter, who runs UAT, or what the security-testing cadence is.
   `test-strategy` therefore decides every change's approach from a fixed default
   layer table rather than from an agreed strategy.
2. **Performance testing is one table row; stress, soak and spike testing are not
   mentioned at all.** No guidance on targets, workload models, baselines,
   environment realism, or what counts as a regression.
3. **Vulnerability testing is named, not designed.** SAST and dependency scanning
   appear as pipeline stages; DAST, fuzzing, container/IaC scanning and penetration
   testing have no skill. `secure-api-review` explicitly says it is not a substitute
   for them, and nothing else fills the gap.
4. **Static code analysis is named, not designed.** No guidance on baselines,
   ratcheting, suppression discipline or rule-change review.
5. **E2E UI automation is generic only.** Good tool-agnostic rules exist, but nothing
   specific for Playwright, Selenium or Cypress, and no cross-browser/device,
   visual-regression or localisation guidance.
6. **Accessibility testing** appears once, as a pipeline stage label.
7. **Functional (requirement) coverage** is implied by the plan table but never
   named as a coverage measure; the case where no coverage tool exists is unhandled.
8. **No test summary / exit report.** Nothing closes a test cycle with a named
   human's go/no-go.

Affected: any team that installs `evidence-discovery` and `evidence-quality` in a
consuming repository — engineers, QA, security and release owners.

## Proposed outcome
- A new `test-strategy-discovery` skill that reads the repository first and then
  interviews the team only for what the repository cannot answer, writing
  `.evidence/context/test-strategy.md` for every testing skill to read.
- Dedicated skills in `evidence-quality` for performance (load, stress, soak, spike,
  capacity), security testing (SCA, secrets, container/IaC, DAST, fuzzing, pen
  testing), static analysis, E2E UI automation (with Playwright, Selenium and
  Cypress references, cross-browser, visual regression, localisation) and
  accessibility.
- Functional coverage, flake detection and the test summary report made explicit in
  the existing skills and templates.

Measurable: each test type named in the problem has a skill or a named section that
gives concrete, checkable rules (not just a table row), each new skill ships with
trigger / non-trigger / behavior eval cases, and `test-strategy` reads the new
profile file.

## Affected users and systems
- Internal: plugin authors (this repo); engineers, QA and release owners in any
  consuming repository.
- Systems: `plugins/evidence-discovery/`, `plugins/evidence-quality/`, docs, README,
  marketplace metadata.

## Regulated record impact
No. Framework guidance only; not itself a regulated record.

## Compliance evidence impact
Not applicable to evidence-chain's own posture (all `[ASK]` in
`.evidence/context/compliance.md`). For consuming repositories, the new skills feed
the existing evidence profile (L0–L3) rather than defining a new one.

## Data classification
None.

## Constraints
- Additive; no existing skill loses behaviour.
- Tool-agnostic: never assume a test tool. Tool-specific material loads only when the
  profile names that tool.
- No new gate. Nothing new may deny a tool call; "blocks vs informs" stays a pipeline
  decision the team records.
- No new external dependency.
- Do not touch files with uncommitted user edits (`testrail-authoring/SKILL.md`,
  `contract-testing/SKILL.md`, `integration-change/SKILL.md`,
  `secure-api-review/SKILL.md`, `gate-plan-exists.sh`,
  `gate-regression-tests.sh`).

## Out of scope
- Installing or configuring any test tool in a consuming repository.
- Mobile-native test automation (Appium, XCUITest, Espresso) — named as a gap.
- Chaos / resilience engineering beyond what stress testing covers.
- Resolving this repository's own `[ASK]` items.

## Open questions
None blocking. The tracker key PILOT-51 follows the repository's sequential PILOT
convention (last used: PILOT-50); the maintainer confirms it at plan approval.
