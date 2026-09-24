---
name: test-automation
description: Write, structure and repair automated tests in the framework the repository actually uses, tagged so a run maps back to tracker issues and manual test cases. Use when automated tests are written or fixed, when a manual case is automated, when a test is flaky, and when someone asks how test results reach the test management system. Read the framework from the repository profile — never assume one.
---

# Test automation

Read `.evidence/context/stack.md` for the actual frameworks, commands and test
locations. This skill is about discipline, not about a particular tool.

## Tag for traceability

Every automated test carries, in whatever tagging mechanism the framework provides:
- the **tracker key** of the change that introduced or last modified it
- the **manual test case ID** it automates, where it automates one

Without both, a green pipeline proves nothing about which requirements were covered,
and the traceability matrix has to be maintained by hand — which means it will not be.

## Structure

- **One behaviour per test.** A test asserting five things tells you nothing useful when
  it fails.
- **Address elements by role and accessible name** where the framework supports it, not
  by brittle structural selectors. This makes tests survive refactors and doubles as an
  accessibility check.
- **No sleeps.** Wait for a condition, never for a duration.
- **Isolate the layers.** End-to-end suites should be thin: the critical journeys only.
  Everything else belongs lower, where it is faster and more stable. For browser
  automation specifics (Playwright, Selenium, Cypress, cross-browser, visual
  regression, localisation), apply `e2e-ui-testing`.

## Test data

- **Deterministic data.** Tests that depend on data left behind by other tests are the
  root of most flake. Each test sets up and tears down its own state.
- **Bulk synthetic data comes from a sample, never from production.** When a test needs
  volume — thousands of rows, not a handful of fixtures — derive it from a small,
  explicitly-approved sample using whatever generation tooling the project already has,
  never from a copy of real production data. Keep provenance traceable: record which
  sample a generated set came from and when, the same way any other test evidence names
  its source rather than asserting a result.
- **Do not trust a language model to generate PII-shaped fields.** AI-generated
  synthetic data is specifically unreliable for fields like national ID numbers,
  payment card numbers, or other checksum- or format-constrained PII — it can produce
  invalid-looking values, or silently fail to generate anything for that field at all.
  Use purpose-built synthetic-data tooling for those fields; do not paper over a gap
  there with a plausible-looking string an agent invented.

## Results back to the test management system

Decide and record: the pipeline maps each automated test to its case ID via the tag,
opens or reuses a run named with the tracker key and build identifier, and posts
results. Check the toolchain profile for whether this session or the pipeline holds the
write credential. **The pipeline should own this write, not an interactive session** —
results are evidence, and evidence should come from the toolchain, not from a
conversation.

## Flake policy

Flake destroys the value of continuous testing faster than anything else, because a
suite people do not trust is a suite people bypass.

- A test that fails intermittently is **quarantined within one working day**, with a
  tracker issue, not left to erode confidence.
- Quarantine is time-boxed. A quarantined test that is not fixed within the agreed
  window is deleted, and its coverage gap is recorded as a risk. Indefinite quarantine
  is a lie about coverage.
- **Never** fix flake by adding a retry to hide it, widening a wait, or loosening an
  assertion. Find the race.
- Flake rate is a tracked metric, not a mood.

**Detecting flake.** A test is flaky when it both passes and fails on the **same
commit** in the same environment. Detect it deliberately, in nightly runs rather than
in the merge gate: rerun failures, run the suite in random order and in parallel, and
compare results across repeated runs of an unchanged commit. A test that failed and
then passed on rerun is recorded as **flaky**, never as passed. It goes straight to
quarantine and `flake-triage`. Detection reruns exist to find flake. The merge-gating
run keeps retries off, so a rerun can never turn red into green there. Flake rate
= flaky tests ÷ tests executed, per week, tracked alongside quarantine count and
quarantine age.

## Interactive browser tooling vs. scripted tests

Driving a browser interactively through an agent is useful for **exploration, test
authoring, and reproducing a bug**. It is not how tests run in the pipeline. Pipeline
runs are deterministic scripted executions. Keep the two clearly separate, and never
present an agent-driven exploratory session as a test run.
