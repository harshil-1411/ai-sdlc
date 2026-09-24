# Cypress — specifics

Load only when the repository profile names Cypress. Check the installed version
before relying on any API named here.

## Command model
- Cypress commands are queued and run asynchronously. Don't assign a command's result
  to a variable. Chain `.then()` or use aliases (`.as()`).
- Assertions retry until timeout (`cy.get(…).should('be.visible')`). Put the
  assertion on the query chain rather than reading a value and checking it once.

## Waiting
- Never `cy.wait(<milliseconds>)`. Wait on a network alias instead:
  `cy.intercept('GET', '/api/orders*').as('orders')` then `cy.wait('@orders')`, or on
  a retrying assertion.

## Locators
- Cypress recommends dedicated `data-cy` / `data-test` attributes. Where
  `@testing-library/cypress` is installed, prefer `cy.findByRole(role, { name })`
  for the accessibility benefit. Avoid selectors on classes, tags or copy text.

## Auth and data
- `cy.session()` to sign in once per role and cache the session across tests.
- Seed data with `cy.request()` or `cy.task()` against the API or database, not
  through the UI.
- Tests must pass in isolation. Don't rely on state from a previous `it` block
  (test isolation is on by default in current versions; keep it on).

## Known constraints to plan around
- One browser tab per test; multi-tab flows need a different approach, such as
  asserting on the link target instead.
- Cross-origin steps need `cy.origin()`.
- Browser coverage is narrower than Playwright or Selenium (Chrome-family and
  Firefox; WebKit is experimental). If `test-strategy.md` requires Safari, record
  the gap or cover Safari with a different tool.

## Configuration
- `retries: { runMode: 0 }` for merge-gating runs. Nightly detection may use
  retries only if the reporter records the test as flaky.
- Screenshots on failure are automatic in `cypress run`. Turn on `video` where the
  evidence profile requires it.
- Use a JUnit or mochawesome reporter with the tracker key and case ID in the test
  title (or via a tagging plugin such as `@cypress/grep`) for upload to test
  management.
- Parallelise with the team's recorded option (Cypress Cloud, or spec splitting
  across CI machines).

## Visual and accessibility
- Visual regression needs a plugin or service. Use the one recorded in the profile,
  with the baseline review rules in SKILL.md.
- `cypress-axe` (`cy.injectAxe()`, `cy.checkA11y()`) for automated accessibility
  scans within journeys.

## Component testing
- Cypress component tests mount a component in isolation. Label them as component
  tests. They don't count as end-to-end journey coverage.
