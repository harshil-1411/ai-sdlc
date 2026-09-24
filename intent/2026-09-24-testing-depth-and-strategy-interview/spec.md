# Spec: Testing depth across every test type, and a test-strategy interview at onboarding
Tracker: PILOT-51   From: intent/2026-09-24-testing-depth-and-strategy-interview/intent.md   Risk tier: 2

Risk classification: Tier 2 per `risk-tiering` — new skills and templates that change
what future sessions do in consuming repositories, plus a one-line change to the
context message of an existing SessionStart script. Not Tier 3: no gate is added or
changed, no deny path exists in any touched script, and no regulated record is
touched.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Requirements

| ID | Requirement | Source | Acceptance |
| --- | --- | --- | --- |
| REQ-TSD-01 | New skill `evidence-discovery:test-strategy-discovery` reads repository evidence first (test configs, test dirs, CI config, reporters, existing profile files) and asks the human only for what the evidence cannot establish, as one numbered batch, most consequential first. | Problem 1 | SKILL.md has a "read before asking" step listing evidence sources and an interview step that excludes anything already `[confirmed]`. |
| REQ-TSD-02 | The skill writes `.evidence/context/test-strategy.md` from a new template: a per-test-type scope table (in / out / deferred, reason, owner, stage, tool), non-functional targets, environments, browser/device matrix, automation vs manual ownership, UAT ownership, security-testing cadence, entry and exit criteria, flake quarantine window, coverage tooling. Every line is marked `[confirmed]` / `[inferred]` / `[ASK]`. | Problem 1 | Template exists in `plugins/evidence-discovery/templates/`; skill references it. |
| REQ-TSD-03 | A test type is never recorded as out of scope silently. "Out" needs a reason and a named decider; otherwise it is `[ASK]`. | Problem 1 | Stated as a rule; behavior eval asserts it. |
| REQ-TSD-04 | `test-strategy` and `continuous-testing` read `test-strategy.md` when present, and state that they are using framework defaults when it is absent. | Problem 1 | Both SKILL.md files reference the profile. |
| REQ-TSD-05 | `require-repo-profile.sh`'s SessionStart message names `test-strategy.md` among the profile files to read. Advisory only, exit 0 preserved. | Problem 1 | Message text updated; `bash -n` passes; script still has no deny path. |
| REQ-PERF-01 | New skill `evidence-quality:performance-testing` covers load, stress, soak, spike, and capacity/scalability testing, each with its purpose and when to run it. | Problem 2 | Section per type in SKILL.md. |
| REQ-PERF-02 | Performance targets must exist as numeric, percentile-based requirements in `spec.md` before a performance test is designed; a missing target is a spec defect, not a guess. | Problem 2 | Rule present; behavior eval asserts the skill refuses to invent a target. |
| REQ-PERF-03 | The skill requires a workload model, a recorded baseline, a stated environment-parity gap, pass/fail criteria fixed before the run, and reporting of percentiles (not averages) with error rate. | Problem 2 | Each is a named rule. |
| REQ-SEC-01 | New skill `evidence-quality:security-testing` covers dependency/SCA scanning, secret scanning, container and IaC scanning, DAST, fuzzing and penetration testing — what each finds, where it runs, what evidence it produces. | Problem 3 | Section per type. |
| REQ-SEC-02 | Findings triage: severity-based fix-time policy read from the profile, suppressions only with reason + owner + expiry, new findings distinguished from a recorded baseline. | Problem 3 | Rules present; behavior eval asserts no unexplained suppression. |
| REQ-SEC-03 | DAST, fuzzing and pen testing run only against non-production environments unless a written authorisation for production exists; the skill never initiates a scan against a target not named in the profile. | Problem 3 | Rule present. |
| REQ-SA-01 | New skill `evidence-quality:static-analysis` covers linting, formatting, type checking, complexity/duplication and SAST rule configuration. | Problem 4 | Section per category. |
| REQ-SA-02 | Baseline-and-ratchet: new and changed code must be clean; pre-existing findings are baselined and the baseline may only shrink. Disabling a rule or adding a suppression to pass a check needs an inline reason and review; rule-set changes are their own reviewed change. | Problem 4 | Rules present; behavior eval asserts the skill refuses to disable a rule to make CI pass. |
| REQ-E2E-01 | New skill `evidence-quality:e2e-ui-testing` covers critical-journey selection, locator strategy, waiting, test data and auth-state isolation, failure artifacts mapped to the evidence profile, parallelism/sharding, cross-browser/device matrix, visual regression with reviewed baselines, and localisation checks. | Problem 5 | Section per topic. |
| REQ-E2E-02 | Tool-specific references `references/playwright.md`, `references/selenium.md`, `references/cypress.md` exist and are loaded only when `stack.md` or `test-strategy.md` names that tool; an unnamed tool gets the general rules and the gap is stated. | Problem 5; Constraint "tool-agnostic" | Three reference files; SKILL.md states the loading rule; behavior eval asserts no tool is assumed. |
| REQ-A11Y-01 | New skill `evidence-quality:accessibility-testing`: the conformance target comes from the profile (`[ASK]` if absent); automated scanning is stated to catch only part of the issues; manual keyboard, screen-reader, zoom/reflow and contrast checks are required for UI changes; results are evidence per the profile. | Problem 6 | Rules present; behavior eval asserts automated scan alone is not accepted as full coverage. |
| REQ-COV-01 | `test-strategy`'s coverage section names requirement (functional) coverage as REQ → passing test, derived from the plan table and traceability matrix; treats diff coverage as reviewer information; and when no coverage tool exists, names the gap instead of installing one ad hoc. | Problem 7 | Section updated. |
| REQ-FLK-01 | `test-automation`'s flake policy defines flake detection (a test that both passes and fails on the same commit) and states that detection reruns record the result as flaky, never as a pass. | Problem — flaky strength | Section updated. Must not contradict "never fix flake by adding a retry". |
| REQ-TSR-01 | New template `evidence-quality/templates/test-summary-report.md` (scope run, results per layer and type, requirement coverage, open defects, accepted gaps, flake and quarantine status, non-functional results vs targets, evidence links, go/no-go by a named human). `test-strategy` instructs producing it at the end of a test cycle; `continuous-testing`'s pre-release stage lists it as evidence. The agent drafts it and never signs it. | Problem 8 | Template exists; both skills reference it. |
| REQ-TSR-02 | `templates/test-plan-section.md` gains entry criteria and a non-functional coverage table. | Problem 8 | Sections present. |
| REQ-INT-01 | `test-strategy`'s layer table lists each new test type and points at its skill; `continuous-testing`'s stage table places performance/stress/soak, DAST, visual regression and accessibility; `test-designer` routes non-functional requirements to the matching skill. | Problems 2–6 | References present in all three files. |
| REQ-DOC-01 | README, `docs/skills-reference.md`, `docs/getting-started.md`, both plugins' `evals/README.md`, both `plugin.json` descriptions and `marketplace.json` reflect the new skills. | Doc drift (PILOT-48 lesson) | Each file mentions the new skills. |
| REQ-EVAL-01 | Each new skill has a trigger, a non-trigger and a behavior eval case under its plugin's `evals/`, following the existing `prompt.md` + `graders/` convention. | Existing eval-case DoD (PILOT-50) | 18 case directories. |

## Design
New files:
- `plugins/evidence-discovery/skills/test-strategy-discovery/SKILL.md`
- `plugins/evidence-discovery/templates/test-strategy.md`
- `plugins/evidence-quality/skills/performance-testing/SKILL.md`
- `plugins/evidence-quality/skills/security-testing/SKILL.md`
- `plugins/evidence-quality/skills/static-analysis/SKILL.md`
- `plugins/evidence-quality/skills/e2e-ui-testing/SKILL.md` and `references/{playwright,selenium,cypress}.md`
- `plugins/evidence-quality/skills/accessibility-testing/SKILL.md`
- `plugins/evidence-quality/templates/test-summary-report.md`
- 18 eval case directories

Division of responsibility, so no two skills own the same rule:
- **static-analysis** owns tool configuration, baseline/ratchet and suppression
  discipline for every static check, SAST included.
- **security-testing** owns dynamic and supply-chain security testing and the
  severity/fix-time policy for security findings from any source, SAST included.
- **secure-api-review** (unchanged) stays the design- and code-review pass.
- **e2e-ui-testing** owns browser automation, cross-browser, visual regression and
  localisation; **accessibility-testing** owns conformance, and e2e-ui-testing
  points at it for automated a11y scans inside journeys.
- **test-strategy** stays the router: it chooses layers and types, and delegates
  depth to the type skills.

Every new skill follows the house conventions: read `.evidence/context/` first, never
assume a tool, blocks vs informs is explicit, evidence is a link, "Never" section.

## Regulatory control impact

| Framework | Control ID | Applies? | How it is satisfied | Evidence |
| --- | --- | --- | --- | --- |
| — none confirmed applicable | — | N/A | Framework guidance only; see `.evidence/context/compliance.md`. | `.evidence/context/compliance.md` |

## Evidence impact
No existing evidence rows change. New skills name evidence artifacts consistent with
the existing L0–L3 evidence profile in `evidence-package`.

## Diagrams
None of the inclusion conditions apply.

## Security design
One security-relevant property: `security-testing` must never tell a session to
launch active scanning (DAST, fuzzing) against a target the profile does not name, or
against production without written authorisation (REQ-SEC-03). `require-repo-profile.sh`
keeps its exit-0, no-deny behaviour (REQ-TSD-05).

## UX
Not applicable.

## Areas of concern
- **Overlap between new skills and existing ones.** `static-analysis` vs
  `security-testing` vs `secure-api-review` on SAST, and `e2e-ui-testing` vs
  `accessibility-testing` on automated a11y scans, could produce conflicting rules.
  Mitigated by the division of responsibility above; each skill cross-references
  rather than restates.
- **Trigger collisions.** Six new skills in a space where `test-strategy`,
  `test-automation` and `continuous-testing` already trigger broadly. A request like
  "set up Playwright" could fire `test-automation` instead of `e2e-ui-testing`.
  Mitigated by specific trigger phrases in each description and by a non-trigger eval
  per skill; residual risk accepted, measured by the eval runs.
- **Stale tool references.** Playwright, Selenium and Cypress APIs change. References
  describe durable practices (locator strategy, tracing, isolation) rather than
  version-pinned API calls, and name the version-sensitive points as "check the
  installed version".
- **Interview fatigue.** A long test-strategy questionnaire at onboarding will be
  abandoned. The skill asks only what the repository cannot answer, in one batch,
  most consequential first, and accepts `[ASK]` left open.
- **Security-testing guidance used against unauthorised targets.** Addressed by
  REQ-SEC-03.

## Rejected alternatives
- **Extend `test-automation` instead of adding `e2e-ui-testing`.** Rejected: UI
  automation, cross-browser, visual regression and localisation are enough material
  that folding them in would bury `test-automation`'s general discipline and weaken
  triggering on "Playwright"/"Selenium" requests.
- **One `non-functional-testing` skill for performance, security and a11y.**
  Rejected: different owners, tools and failure modes; one skill would trigger
  poorly and each section would stay shallow, which is the problem being fixed.
- **Hard-coding a default tool (e.g. Playwright, k6, OWASP ZAP).** Rejected:
  violates the "never assume a tool" design commitment.
- **A hook that blocks when `test-strategy.md` is missing.** Rejected: onboarding
  would be blocked mid-thought; a missing profile is surfaced as context instead,
  consistent with `require-repo-profile.sh`.
