# Selenium / WebDriver — specifics

Load only when the repository profile names Selenium, WebdriverIO or a Selenium Grid.
Check the language binding and version in use before relying on any API named here.

## Driver lifecycle
- One driver session per test, or per worker with full state reset. Always `quit()` in
  teardown, including on failure. Leaked sessions exhaust a Grid.
- On Selenium 4.6+, Selenium Manager resolves browser drivers. Don't commit driver
  binaries or hand-managed driver-download scripts unless the profile records why.
- For parallel runs in Java/C#, hold the driver in a thread-local (or the framework's
  equivalent) so tests never share a session.

## Waiting
- Use **explicit waits** (`WebDriverWait` with expected conditions: visibility,
  clickability, staleness, URL). Keep the implicit wait at zero.
  **Do not mix implicit and explicit waits.** Selenium documents that mixing them
  causes unpredictable wait times.
- Never `Thread.sleep` / `time.sleep` in a committed test.
- Wait on staleness after navigation-causing clicks, so the next lookup doesn't hit
  the old page.

## Locators
- WebDriver has no built-in role locator. In order of preference: a dedicated test
  attribute (`By.cssSelector("[data-testid=…]")`), a stable `id`, `name`, or ARIA
  attributes (`[aria-label=…]`). Avoid XPath on structure and generated class names.
- Put locators in **page objects** (or component objects) so a UI change is fixed
  in one place. Page objects expose intent (`ordersPage.approve(orderId)`), not raw
  clicks, and contain no assertions.

## Cross-browser
- Selenium Grid (or a cloud grid) runs the `test-strategy.md` matrix. Set
  capabilities per browser. Record the Grid and browser versions in the run
  evidence.

## Evidence
- In the failure hook, capture `TakesScreenshot`, the page source, and the browser
  logs (BiDi or CDP log access where supported). Name the files with the tracker key and case ID.
- Emit JUnit XML (or TestNG/NUnit equivalent) with the tracker key and case ID in
  the test name or a category/tag, for upload to test management.

## Traceability tags
- JUnit 5 `@Tag`, TestNG `groups`, NUnit `[Category]`, pytest markers. Use
  whichever the framework provides, carrying both the tracker key and the case ID.

## Visual and accessibility
- Selenium has no built-in visual comparison. Use the visual tool recorded in the
  profile, with the baseline review rules in SKILL.md.
- Use axe-core's Selenium integration for your language for automated accessibility
  scans within journeys.

## Retries
- Framework rerun options (Surefire `rerunFailingTestsCount`, TestNG retry
  analyzers, pytest-rerunfailures) must be **off** for merge-gating runs. If used in
  nightly runs for detection, record the result as flaky, not passed.
