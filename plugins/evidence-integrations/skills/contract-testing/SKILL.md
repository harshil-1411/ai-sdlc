---
name: contract-testing
description: Establish and maintain contract tests so integration breakages are caught in the pipeline instead of in production. Use whenever an integration is added or changed, whenever a partner publishes a new API version, whenever an integration incident is investigated, and whenever a spec relies on an external system behaving a particular way. Trigger specifically when a contract test starts failing and someone proposes updating the contract/fixture/stub file to match the partner's new response so the test passes again — establish whether it's your code, their contract, or a misunderstanding before touching the contract file; treat that request the same as "update the test to match the bug." Never rely on a shared staging environment as the only proof an integration works.
---

# Contract testing

End-to-end tests against a partner's sandbox are slow, flaky, and dependent on someone
else's uptime. Contract tests are fast, run every commit, and fail for a reason you can
act on.

## What to build, in priority order

1. **Consumer contract tests.** For each external call you make: record the request you
   send and the response shape you depend on. Run against a stub built from that
   contract on every commit. This catches *your* drift immediately.
2. **Schema validation on the boundary.** Validate every inbound payload against a
   schema and reject unknown or malformed fields loudly. Half of integration incidents
   are a partner quietly adding or renaming a field.
3. **Provider verification, where the partner supports it.** If they publish a contract
   or an OpenAPI spec, verify against it on a schedule so their changes surface as a
   pipeline failure rather than a production one.
4. **A scheduled sandbox smoke test.** A small number of real calls against the
   partner's sandbox, nightly, proving the credential still works and the endpoint still
   exists. Keep it small — this is a canary, not a test suite.

## Rules

- **The stub is generated from the recorded contract, never hand-written from the docs.**
  Hand-written stubs encode what you believe the partner does, so they agree with your
  code and both are wrong together.
- **Re-record contracts on a schedule**, not just when something breaks. A stale contract
  passing is worse than no contract.
- **Version the contracts** and keep the old one until the migration completes, so you
  can test both sides of a partner version bump.
- **Test the failure paths.** Timeout, 500, 429, malformed body, and a response that is
  valid but semantically wrong. Most integration code handles the happy path and falls
  over on the second one.
- **Test idempotency explicitly.** Send the same request twice and assert the effect
  happened once. In a regulated product this is the test that prevents a duplicate
  regulated action.

## When a contract test fails

It means one of: your code changed, their contract changed, or your understanding was
wrong. Establish which before changing anything. Updating a contract to make a test pass
is exactly as bad as editing a test to make a fix pass, and the same rule applies.
