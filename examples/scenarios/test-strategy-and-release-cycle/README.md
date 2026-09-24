# Scenario: from a test-strategy interview to a signed release go/no-go

**Who this is for:** a QA lead or engineering manager adopting this framework who
wants to see how the testing side works end to end. It covers what the team is
asked at onboarding, how a single change's performance, accessibility, UI and
security requirements get planned and proven, and what closes the test cycle.
Read [the non-regulated feature scenario](../new-feature-non-regulated/README.md)
first for the core intent → spec → plan loop. This scenario focuses only on testing.

## The setting

A B2C retail web app. No regulatory obligation (`compliance.md` records "none apply",
with a named confirmer). The stack profile already exists. `stack.md` shows a
TypeScript frontend and API, Jest for unit tests, and Playwright for E2E.
`toolchain.md` shows GitHub Actions and a tracker with `SHOP-` keys.

## Part 1 — onboarding: the test-strategy interview

**1 · Read before asking.** On the first "what testing should we be doing?",
`test-strategy-discovery` reads the repository before saying anything:

| Found | Marker | Evidence |
| --- | --- | --- |
| Unit: Jest, runs on every push | `[confirmed]` | `jest.config.ts`, `ci.yml` job `unit` |
| E2E: Playwright, **Chromium project only** | `[confirmed]` | `playwright.config.ts` has one project |
| Lint + type check on push | `[confirmed]` | `ci.yml` jobs `lint`, `typecheck` |
| Dependency scanning | `[inferred]` | `.github/dependabot.yml` exists, but no job fails the build on it |
| 14 tests marked `test.skip` with no linked issue | `[confirmed]` | grep of `e2e/` |
| Performance, DAST, accessibility, visual regression | none found | — |

**2 · One batch of questions, most consequential first.** The team gets seven
questions, not seventy. Everything the repository already proved is left out:

1. Performance, accessibility, DAST, visual regression, cross-browser: in, out or
   deferred? Who decides?
2. Latency and throughput targets for search and checkout, as numbers?
3. Accessibility conformance target?
4. Which environment is production-like, and where are load and active scanning allowed?
5. Browser/device matrix: what runs on every PR, and what runs nightly?
6. Who owns UAT, and who signs the release go/no-go?
7. What should happen to the 14 skipped tests: quarantine with issues, or delete and record the gap?

**3 · The pushback that matters.** A developer answers question 1 with "we don't
need performance or security testing, skip those." The skill doesn't record that as
`out`. A type goes out of scope only with a reason and a named decider, so both rows
become `[ASK]` and the question goes to the engineering lead. The lead's answer:
performance is **in**, because a seasonal sale doubles traffic. DAST is **deferred**
to next quarter: *"deferred; no staging auth fixture yet; decided by the engineering
lead, 2026-09-24; revisit 2026-12-01"*. That is now a recorded risk acceptance with
a name and a date, not a silent gap.

**4 · The profile.** An excerpt of `.evidence/context/test-strategy.md`:

| Test type | Scope | Decided by | Stage | Tool | Marker |
| --- | --- | --- | --- | --- | --- |
| E2E UI | in | — | PR smoke + nightly full | Playwright | `[confirmed]` |
| Cross-browser | in: Chromium on PR; Firefox, WebKit, Pixel 7 viewport nightly | QA lead | nightly | Playwright projects | `[confirmed]` |
| Accessibility | in, WCAG 2.2 AA | product owner | PR (automated) + pre-release (manual) | axe via `@axe-core/playwright` | `[confirmed]` |
| Performance — load, spike | in | engineering lead | nightly + pre-release | k6 | `[confirmed]` |
| Performance — soak | deferred to Q1, no production-like env yet | engineering lead | — | — | `[confirmed]` |
| DAST | deferred, revisit 2026-12-01 | engineering lead | — | — | `[confirmed]` |
| Visual regression | out, UI changes weekly and baselines would churn | QA lead | — | — | `[confirmed]` |

Search latency target: p95 < 400 ms and p99 < 900 ms at 150 req/s, error rate
< 0.5% `[confirmed]`, product decision recorded in the tracker. Flake quarantine
window: 5 days. Go/no-go signer: the QA lead.

## Part 2 — one change, proven across every type it touches

**The story (SHOP-412):** "As a shopper, I want to search my order history by
product name, so I can re-order quickly." `risk-tiering` puts it at **Tier 2**
(new endpoint, customer data, performance-sensitive path).

**5 · Every non-functional expectation becomes a numbered requirement.**
`spec-and-design` writes REQ-ORD-01 to REQ-ORD-03 as functional requirements, and adds:

- **REQ-ORD-04:** search p95 < 400 ms / p99 < 900 ms at 150 req/s, error rate < 0.5%,
  over 2 years of order history
- **REQ-ORD-05:** the search panel meets WCAG 2.2 AA
- **REQ-ORD-06:** a shopper can only ever see their own orders (object-level authorisation)

An earlier draft said "search should be fast". `test-designer` flagged that as a spec
defect under its non-functional routing rule ("a requirement with no number is not
testable") instead of designing a test around it.

**6 · The plan's test section.** `test-strategy` reads the profile, routes each
type to its skill, and produces:

| REQ ID | Layer | Automated? | Test case ID | Automated test | Evidence produced |
| --- | --- | --- | --- | --- | --- |
| REQ-ORD-01 | Unit | Yes | — | `orderSearch.spec.ts` | CI JUnit report, run ID |
| REQ-ORD-02 | Integration / API | Yes | — | `orders.search.api.spec.ts` | CI JUnit report, run ID |
| REQ-ORD-03 | E2E | Yes | C9012 | `e2e/reorder-from-search.spec.ts @SHOP-412 @C9012` | Playwright report; trace on failure |
| REQ-ORD-06 | Integration / security | Yes | — | `orders.search.authz.spec.ts` (second shopper, forged order IDs) | CI JUnit report |

**Non-functional coverage:**

| REQ ID | Type | Target | Owning skill | Environment | Stage | Evidence produced |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-ORD-04 | Load + spike | p95 < 400 ms, p99 < 900 ms @ 150 req/s, errors < 0.5% | `performance-testing` | `perf` (gap stated: 2 API replicas vs 6 in prod) | nightly + pre-release | k6 summary export, run ID, server metrics link |
| REQ-ORD-05 | Accessibility | WCAG 2.2 AA | `accessibility-testing` | `staging` | PR (axe) + pre-release (manual) | axe report; manual checklist with tester, date, AT/browser versions |

**Entry criteria:** build deployed to `perf` and `staging`; 2 years of synthetic
order history seeded in `perf` from the approved sample; REQ-ORD-04's targets
present in `spec.md`.

## Part 3 — the rules doing their job

**7 · The threshold that wasn't moved.** The first pre-release load run shows
p95 = 460 ms. A developer suggests raising the k6 threshold to 500 ms, "since it's
close". `performance-testing` refuses: thresholds are fixed before the run, and
changing one after seeing the result is like loosening an assertion. Server metrics
from the same window show a sequential scan on `order_items.product_name`. After an
index was added (its own reviewed migration), p95 = 210 ms. The fix is recorded
against a new baseline for the same workload model and environment.

**8 · The clean scan that wasn't enough.** axe reports zero violations on the
search panel. `accessibility-testing` still requires the manual checks. Keyboard-only
testing finds that focus is trapped in the results dropdown: Escape does nothing.
Automated scanning cannot catch this. The defect is fixed, and a scripted keyboard
check is added to the E2E journey so it can't come back.

**9 · The suppression that needed an owner.** A new dependency brings a medium
CVE in a transitive package. The build doesn't block, because it's below high and
not new on the default branch. The developer wants to add it to the ignore file
anyway. `security-testing` accepts a suppression only with its reason (the vulnerable
function is unreachable, with a link to the call-graph check), an owner, the approver
named in the profile, and an expiry date of 30 days. When it expires, the finding
reopens.

**10 · The lint rule that stayed on.** CI fails on `no-floating-promises` in the new
search handler. A request to add `/* eslint-disable */` is declined under
`static-analysis`: the two real unhandled promises are fixed. A proposal to relax
the rule repo-wide is opened as its own change, and it doesn't ride along in SHOP-412.

**11 · The flake that got caught.** Nightly flake detection reruns failures on the
same commit. `reorder-from-search` fails once on WebKit and passes on rerun. It's
recorded as **flaky**, not passed, and quarantined with SHOP-431. `flake-triage`
classifies it as a **real defect**: a race between the search debounce and the
results render, which only shows on the slower engine. Fixed within the 5-day window.

## Part 4 — closing the cycle

**12 · The test summary report.** At pre-release, `test-strategy` drafts
`templates/test-summary-report.md` from linked evidence only. Excerpt:

| Section | Content |
| --- | --- |
| Requirement coverage | 6 of 6 requirements have a test that ran and passed |
| Non-functional | REQ-ORD-04: p95 210 ms / p99 520 ms @ 150 req/s, errors 0.1%, pass, with the environment gap stated (2 vs 6 replicas). REQ-ORD-05: pass (axe + manual checklist) |
| Security | 0 new critical/high; 1 medium suppressed until 2026-10-24, owner and approver named |
| Flake | SHOP-431 fixed; 14 legacy skips: 9 quarantined with issues, 5 deleted with the coverage gap recorded |
| Accepted gaps | DAST deferred (engineering lead, revisit 2026-12-01); soak deferred (no production-like environment) |
| Decision | *Left blank by the agent.* Go, signed by the QA lead, 2026-10-02 |

The agent drafted every row except the decision. The go/no-go belongs to the named
human in the profile.

## What made this different

Before `test-strategy-discovery`, this change would have been planned from the
default layer table. Nobody would have asked whether performance mattered, so
REQ-ORD-04 might never have existed, and the sequential scan would have shipped
into the seasonal sale. The interview didn't add ceremony. It made the team
decide, once and on the record, which risks they test for and which they accept.

## Read next

- [`test-strategy-discovery`](../../../plugins/evidence-discovery/skills/test-strategy-discovery/SKILL.md): the interview, and "nothing is out of scope silently"
- [`test-strategy`](../../../plugins/evidence-quality/skills/test-strategy/SKILL.md): routing to type skills, functional coverage, before and after a test cycle
- [`performance-testing`](../../../plugins/evidence-quality/skills/performance-testing/SKILL.md): "No target, no test", and thresholds fixed before the run
- [`accessibility-testing`](../../../plugins/evidence-quality/skills/accessibility-testing/SKILL.md): why a clean automated scan is necessary, not sufficient
- [`security-testing`](../../../plugins/evidence-quality/skills/security-testing/SKILL.md): the findings and suppression policy
- [`static-analysis`](../../../plugins/evidence-quality/skills/static-analysis/SKILL.md): rule changes are their own change
- [`e2e-ui-testing`](../../../plugins/evidence-quality/skills/e2e-ui-testing/SKILL.md) and its [Playwright reference](../../../plugins/evidence-quality/skills/e2e-ui-testing/references/playwright.md)
- [`test-automation`](../../../plugins/evidence-quality/skills/test-automation/SKILL.md): detecting flake without hiding it
- [Scenario: proving a regulated-record case](../qa-evidence-profile/README.md): the same testing flow when a Tier 3 record and L3 evidence are involved
