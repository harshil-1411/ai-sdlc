---
name: e2e-ui-testing
description: Design, write and stabilise end-to-end browser UI tests — critical-journey selection, locators, waiting, test data and auth-state isolation, failure artifacts as evidence, parallelism and sharding, cross-browser and device coverage, visual regression, and localisation checks — using whatever browser automation tool the repository actually uses (Playwright, Selenium/WebDriver, Cypress or another). Use this whenever someone asks to write, fix, speed up or organise E2E or UI tests, set up Playwright, Selenium or Cypress, add cross-browser or mobile-viewport coverage, add screenshot or visual regression tests, or test the UI in another language or locale. Read the tool from the repository profile — never assume one.
---

# End-to-end UI testing

Read `.evidence/context/stack.md` and `test-strategy.md` for the browser automation
tool, the browser/device matrix, and whether visual regression and localisation are
in scope. Then load the matching reference **only if the profile names that tool**:

- Playwright → `references/playwright.md`
- Selenium / WebDriver (including WebdriverIO and Selenium Grid) → `references/selenium.md`
- Cypress → `references/cypress.md`

If the profile names none, or names a tool with no reference here, apply the general
rules below and say that no tool-specific guidance was applied. Never pick a tool on
the team's behalf. Adopting one is a planned change.

`test-automation` still applies: traceability tags, one behaviour per test,
deterministic data, and the flake policy. This skill adds what is specific to driving
a real browser.

## Keep the E2E layer thin

E2E tests are the slowest and flakiest layer. Use them for **critical user journeys
through the real UI**: sign-in, the core business flow, payment or approval, anything
regulated where the displayed result is itself the requirement. Validation rules,
calculations and permissions are proven at unit or API level (`test-strategy`).

Keep a written list of critical journeys in the test plan. A new E2E test that is not
on that list needs a reason.

## Locators

Order of preference:
1. **Role and accessible name** (button "Submit", heading "Orders"). This survives
   refactors and doubles as an accessibility check.
2. **Label text** for form fields.
3. **A dedicated test attribute** (`data-testid` or similar) where there is no stable
   accessible name, agreed with the frontend team.
4. **Never** positional or deep structural selectors (`div > div:nth-child(3)`),
   generated class names, or visible text that changes with locale or copy edits.

## Waiting

Wait for a **condition**, never a duration: element visible, request finished, URL
changed, spinner gone. Use the tool's auto-waiting assertions. A fixed sleep is either
too short and flaky, or too long and slow. Usually both, on different machines.

## Test data and auth state

- Each test creates the data it needs, **through the API or a seeding hook, not the
  UI**, and cleans up or uses a unique namespace. Only the journey under test goes
  through the UI.
- Sign in **once per role** and reuse the saved session state. Only the sign-in
  test itself exercises the sign-in form.
- Tests never depend on order or on another test's data. Run them in random order or
  in parallel to prove it.

## Network

Real backend by default in the deploy-to-test stage. Stub third-party services at the
network layer (see `contract-testing`). Stub your own backend only in component-level
UI tests, and label those clearly. A journey test with a stubbed backend proves the
frontend only.

## Failure artifacts are evidence

Configure the tool to keep, **on failure**: a screenshot, a trace or step log, the
console log, and network activity. Record video where the evidence profile (L0–L3 in
`evidence-package`) requires it for critical workflows. Name artifacts with the
tracker key and test case ID so they link into the traceability chain. Store them
where the pipeline publishes evidence, not on a developer laptop.

## Parallelism and speed

- Tests must be independent so they can run fully parallel. Shard across CI
  machines once a suite runs longer than the stage budget in `continuous-testing`.
- On a PR, run a smoke subset of critical journeys on the primary browser. Run the
  full suite and the full browser matrix in the deploy-to-test and nightly stages.

## Cross-browser and device coverage

Take the matrix from `test-strategy.md`. If there is none, ask. Do not default to
"all browsers".
- A **primary** browser runs on every PR.
- **Secondary** browsers and mobile viewports run nightly and pre-release.
- Emulated mobile viewports test layout, not real device behaviour. If real-device
  coverage is in scope, it runs on a device farm and is recorded as such.
- A failure on only one browser is a real defect until shown otherwise. Never skip
  the test for that browser silently. Quarantine it with a tracker issue per the
  flake policy.

## Visual regression

Only if in scope in `test-strategy.md`.
- Screenshot **components or stable regions**, not whole pages full of dynamic
  content. Mask or freeze timestamps, avatars, ads and animations.
- Generate baselines in the **same environment** that runs the comparison (same OS,
  browser build, fonts and device scale factor). Baselines taken on a laptop and compared
  in CI produce noise.
- **A baseline update is a reviewed change.** The person named in
  `test-strategy.md` approves it after looking at the diff images. Never bulk-accept
  updates to turn a run green.
- Keep diff thresholds tight. Loosening one to pass is loosening an assertion.

## Localisation

Only if in scope. For each supported locale, check on the critical journeys:
- no untranslated keys or fallback-language strings
- text expansion doesn't truncate or overlap (German and Finnish run long)
- right-to-left layouts mirror correctly
- dates, numbers, currencies and sorting follow the locale
- locators do not depend on translated text (role plus accessible name in the tested
  locale, or test attributes)

A pseudo-localisation run (accented, lengthened strings) catches most of these
without translations.

## Accessibility inside journeys

Run the tool's automated accessibility scan on each critical page within the
E2E suite. It catches part of the issues only. Conformance testing, including manual
keyboard and screen-reader checks, is owned by `accessibility-testing`.

## Interactive browsing is not a test run

Driving a browser through an agent is for exploration, authoring and reproducing bugs
(see `test-automation`). Pipeline evidence comes only from scripted runs.

## Never

- Never use fixed sleeps.
- Never gate a merge with retries turned on. A retry that turns red into green hides
  flake (see `test-automation`).
- Never bulk-accept visual baselines, or loosen a diff threshold to pass.
- Never set up data through the UI when an API or seed exists.
- Never assume a tool, a browser matrix or a locale list.
