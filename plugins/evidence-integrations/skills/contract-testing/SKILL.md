---
name: contract-testing
description: Establish and maintain contract tests (consumer-driven or OpenAPI-based, tool chosen from the stack profile) so integration breakages fail the pipeline instead of production. Use when an integration is added or changed, a partner ships a new API version, or a spec relies on external behaviour. Trigger when someone proposes updating a contract, fixture or stub to match a partner's new response so a failing contract test passes. Never rely on shared staging as the only proof.
---

# Contract testing

End-to-end tests against a partner's sandbox are slow, flaky, and dependent on someone
else's uptime. Contract tests are fast, run every commit, and fail for a reason you can
act on.

## Choose the tooling from the profile

Read `.evidence/context/stack.md` and `toolchain.md` for what the repository already
uses. Name the tool you would use and why; never assume one. If the profile does not
settle it, list the options below that fit the stack and ask. The common options:

| Need | Options |
| --- | --- |
| Consumer-driven contracts between services you and the partner both control | Pact (with a Pact Broker or PactFlow to share contracts and record verification) |
| Validating traffic or a provider against a published OpenAPI description | Schemathesis (property-based tests generated from the spec), Prism (mock server and validation proxy), or the stack's own OpenAPI request/response validator |
| Catching a breaking change between two versions of an OpenAPI description | openapi-diff, oasdiff, or an equivalent diff check in CI |
| Event and message contracts | AsyncAPI tooling, or Pact message pacts |

Consumer-driven contracts need the provider to run verification. When the partner is an
external vendor who will not, use OpenAPI-based validation against their published
description plus your recorded consumer contract.

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
