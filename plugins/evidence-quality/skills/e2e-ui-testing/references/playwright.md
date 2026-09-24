# Playwright — specifics

Load only when the repository profile names Playwright. Check the installed version
(`package.json` or the lock file, or the Python/Java/.NET package) before relying on
any API named here. The practices are stable; option names occasionally change.

## Locators and assertions
- Prefer `getByRole(role, { name })`, then `getByLabel`, `getByPlaceholder`, and
  `getByTestId` (configure `testIdAttribute` if the team's attribute is not
  `data-testid`).
- Use web-first assertions (`await expect(locator).toBeVisible()`,
  `toHaveText`, `toHaveURL`). They auto-wait and retry until timeout.
  Avoid reading a value and then asserting on it with a plain `expect`.
- Never `page.waitForTimeout()` in a committed test. Wait on a locator assertion,
  `page.waitForResponse`, or `waitForURL`.

## Configuration (`playwright.config`)
- `projects`: one per browser or device in the `test-strategy.md` matrix. Use a
  `setup` project that signs in once per role and saves `storageState`, and make
  the others depend on it.
- `fullyParallel: true` once tests are independent. In CI, use `--shard=i/n`
  across machines and merge the blob reports.
- `retries: 0` for any run that gates a merge. Nightly flake detection may use
  retries **only** so Playwright reports the test as `flaky`. That status goes to the
  flake policy, never counts as a pass.
- `use.trace: 'retain-on-failure'`, `screenshot: 'only-on-failure'`, and
  `video: 'retain-on-failure'` where the evidence profile requires video.
- `webServer` to start the app for local and CI runs, so tests never assume a server
  that someone forgot to start.

## Traceability
- Tag tests with the tracker key and case ID. Use the `tag` option (`{ tag:
  ['@PROJ-123', '@C4567'] }`) on versions that support it, otherwise put them in the
  title. Filter with `--grep`.
- Use `test.step()` to name steps so the trace and report read like the manual case.
- Output a JUnit or JSON reporter for the pipeline's upload to test management.

## Network and data
- `page.route()` to stub third parties. `request` fixture (API testing) to seed data
  before the UI step.
- Fixtures (`test.extend`) to create and clean up per-test data.

## Visual and accessibility
- `await expect(page.getByRole('main')).toHaveScreenshot()` with `mask` for dynamic
  regions and `animations: 'disabled'`. Baselines are per-platform. Generate them
  in the CI container image (the official Playwright Docker image) so local and CI
  rendering match. `--update-snapshots` output is a reviewed change.
- `@axe-core/playwright` (`AxeBuilder`) for automated accessibility scans within
  journeys.

## Locale
- `use: { locale, timezoneId }` per project to run journeys in each supported locale.
