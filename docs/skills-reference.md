# Skills reference

This page lists every skill in Evidence Chain's five plugins (30 skills), with three
things for each:

- **Triggers on**: the "Use …" part of the skill's own `SKILL.md` frontmatter
  `description`, verbatim as of v2. The descriptions were trimmed in v2, so a trigger
  phrase that no longer appears here is no longer part of the description.
- **Produces**: summarised from the skill's body.
- Any "alongside" relationships the source documents.

The agents are listed [at the end](#agents). For how the plugins fit together, see
[concepts.md](concepts.md).

---

## `plugins/evidence-discovery`

| Skill | Triggers on | Produces |
| --- | --- | --- |
| `stack-discovery` | Use on the first session in a repo, when .evidence/context/ is missing or stale, and on any question about languages, runtimes, frameworks, datastores, build tooling or deployment targets ("what stack", "what framework", "what database", "what does this repo use") — even when a README seems to answer it. Ask when evidence is ambiguous. | `.evidence/context/stack.md` and `.evidence/context/deployment.md`, written from templates, each line marked `[confirmed]`/`[inferred]`/`[ASK]`; finishes by presenting the `[ASK]` list as numbered questions and blocks any spec/plan on an unresolved one. |
| `toolchain-discovery` | Use at onboarding, when a workflow needs a tool the session cannot reach, and on "can you access our Jira/GitHub/CI", "are we connected to X", "what's our tracker", "what CI do we use". Establish connectivity as fact, not assumption. | `.evidence/context/toolchain.md` (per tool: use, connectivity class — `MCP-official`/`MCP-community`/`MCP-internal`/`CLI`/`REST-scripted`/`Manual`, credential source, scope, owner, unreachable-fallback) and `.evidence/adapter.yml` (generated from `.evidence/adapter.example.yml`'s field list: `requirements_source`, `spec_glob`, `requirement_pattern`, `tracker_pattern`, `test_dir_segments`, `artifact_chain`, `test_results_location`). |
| `design-system-discovery` | Use at onboarding, before UI or frontend planning, when a new component is proposed, and on questions like "what component library do we use", "what UI kit", "what CSS framework", "do we have a design system" — even when a style guide seems to answer it. | `.evidence/context/design-system.md` — source of truth (package vs. in-repo vs. design-tool-only), tokens and where defined, conventions, accessibility baseline; sets the standing rule that a new component needs written justification in `plan.md`. |
| `compliance-discovery` | Use at onboarding, when a new market or customer segment is entered, and on plain questions like "are we HIPAA/SOC2/GDPR/PCI compliant", "is this regulated", "what regulations apply to us" — even when a README seems to answer it. Never assume a framework applies, and never assume none does. | `.evidence/context/compliance.md` — industry/markets, jurisdictions, each applicable framework with its role (legal/contractual/certified/claimed) and named owner, regulated-record definition, "none apply" recorded as a real answer when true; each entry marked `[confirmed]`/`[inferred]`/`[ASK]`. |
| `test-strategy-discovery` | Use at onboarding, when that file is missing or stale, and on "what's our test strategy", "set up our QA approach", "which browsers do we support", "who does UAT". | `.evidence/context/test-strategy.md` — per-test-type scope (in/out/deferred, with reason and named decider for anything not in), non-functional targets as numbers, environments and where active scanning/load is allowed, browser/device matrix, manual/UAT/go-no-go owners, security fix-time and pen-test cadence, entry/exit criteria, flake window, coverage tooling; read from the repo first, then one numbered batch of questions; each line `[confirmed]`/`[inferred]`/`[ASK]`. |
| `document-ingestion` | Use at adoption and on statements like "we have existing SOPs in Word or PDF", "convert this document", "we already have a requirements spec". Never just retype a controlled document. | Markdown working copies of controlled documents (SOPs, protocols, specs, audit reports), each carrying a header naming source document ID/version/system-of-record and stating "the controlled document is the record"; a recorded source-of-truth decision per document class (repo-authoritative / legacy-authoritative / linkage-only) written into `.evidence/context/`. |

## `plugins/evidence-sdlc`

| Skill | Triggers on | Produces |
| --- | --- | --- |
| `intent-capture` | Use whenever anyone — product, support, UX, QA, sales engineering, or on-call — starts describing something they want built, changed or fixed, even without saying "intent", "requirement" or "story". Capture it here before anyone designs. | `intent/<yyyy-mm-dd>-<slug>/intent.md` from the template — problem, affected users, regulated-record and evidence-impact answers, data classification, measurable "better," explicit out-of-scope, committed to git with author/timestamp. |
| `spec-and-design` | Use when an intent is accepted, when someone asks for a design, solution approach or technical approach, and on direct design requests — "design the schema", "design the data model", "design the API", "what should the table look like", "what fields do we need". Never jump from intent to code. | `spec.md` next to `intent.md` — `REQ-<area>-<nn>` requirements traced to `intent.md`, a regulatory control table per applicable framework, evidence impact, security design notes, data classification/residency, UX states, and an "areas of concern" section routed to named owners; unverified claims marked `[NEEDS VERIFICATION]`, and for a consequential claim, an evidence tier (1-5, regulation/telemetry down to inference-alone) paired with a support classification (supported / conditionally supported / weakly supported / unverified / contradicted); when the "genuinely close design decision" rule fires, a named review trigger and a reversibility line stated across reversibility, coupling, portability and switching cost, written into `spec.md`'s "Rejected alternatives" section. |
| `codebase-grounded-planning` | Use at the start of every implementation session, when someone says "plan this", "how would we build this", "break this down", asks for tasks or a work breakdown, or a session is about to edit code without an approved plan. | `plan.md` (or `plan/<TRACKER-KEY>.md` for concurrent sessions) from the template — real file paths only, a "Files claimed" section, a test-plan row per `REQ-` ID (via `test-strategy`), ordered/risk-stated work, committed before implementation begins; when the engineer corrects the agent on something non-obvious mid-session, a proposed line for `CLAUDE.md`'s "Things Claude gets wrong here" section, confirmed at the same review that approves the diff. |
| `risk-tiering` | Use at the start of every intent, spec and plan, when someone asks "what tier is this", "how much process does this need", "what review does this need", or checks a Definition of Ready or Done, and before proposing any gate. | A stated Tier 1/2/3 classification with a one-line reason, and the matching tiered Definition of Ready and Definition of Done for the change. |
| `secure-api-review` | Use when code creates or changes an API route, authentication, authorization, tenancy, tokens, key material or file upload, when an OpenAPI spec is generated, and on "security review", "threat model", or "I added an endpoint, can you review it" — including code pasted into the request. | A findings table: `Severity (Critical/High/Medium/Nit) \| Location \| What \| Why it matters here \| Suggested fix`, scoped deliberately to tenancy, regulated-record definition, audit-event requirements, residency rules and supply-chain policy — not the generic vulnerability classes a scanner already covers. |
| `agent-trust-boundaries` | Use when designing or reviewing anything that feeds external content to a model or gives an agent a tool over user-supplied data. Trigger on "is this safe to feed to the model", "could this be a prompt injection", "can a customer's ticket steer the agent". | A boundary-by-boundary control check (structural separation, least tool surface, no standing credentials, deterministic authorisation, output-as-untrusted, agent action audit, blast-radius statement) and, for an in-product agent, a flag that it needs its own validation/risk-assessment/regulatory mapping as "a regulated computerised system in its own right." |
| `legacy-characterization` | Use before modifying a thinly tested module, before a refactor or framework upgrade, when someone calls code scary, risky, legacy or not understood, and when onboarding an old repository. | Characterization tests (captured current behaviour, not intended behaviour) committed on their own before any behavioural change, with suspected-bug behaviour marked `// CHARACTERIZATION: current behaviour, believed incorrect`; for regulated modules, explicit assertions on which audit events fire, in what order, with which fields. |
| `root-cause-analysis` | Use when someone says "this is broken", "why is this failing", "debug this", "production issue", "it works locally but not in X", pastes a stack trace or error log, or reports unexpected behaviour. Refuse to theorise until the facts are established. | A failing test committed alone (proving the bug) before any fix, then a findings table: `Symptom \| Trigger \| Root cause \| Evidence for that conclusion \| Assumptions \| Edge cases this also affects \| Proposed fix \| Test that proves it`; for regulated records, a pointer to `governance/deviation-capa-runbook.md`. |
| `schema-migration` | Use when anyone says "migration", "alter the schema", "add a column", "backfill", "rename a field", "drop a table", "reindex", and on any edit under a migrations directory. Migrations are hard to test and expensive to reverse. | A migration proposal stating, in order: which expand-contract phase this is, the backward-compatibility argument for that phase, the backfill verification plan (count check + sample correctness + zero-remaining-rows query, or "no backfill needed" with why), the rollback plan (tested, or explicitly irreversible with why), regulated-record checks (or "not a regulated table" with why), and the risk tier. |
| `release-readiness` | Use when someone says "release", "ship it", "go/no-go", "cut a release", "rollback plan", "ready to deploy", or asks whether a build can go out. The agent drafts evidence; it never signs, approves, or supplies a release approval. | A pre-release checklist, a drafted test summary report (evidence-quality's `templates/test-summary-report.md`) built only from linked evidence, rollback-rehearsal evidence, open defects and the required sign-offs, with go/no-go blockers listed. The decision cell is left blank for the named human. It dispatches the `release-manager` agent and never sets or suggests `RELEASE_APPROVAL`. Invoked by `/evidence-sdlc:release-report`. |

## `plugins/evidence-quality`

| Skill | Triggers on | Produces |
| --- | --- | --- |
| `test-strategy` | Use during spec and plan, whenever someone asks how something will be tested, whenever a requirement has no named test, and before any test is written. Read the repository profile for the actual test frameworks rather than assuming any. | The test-plan table for `plan.md`: `REQ ID \| Layer \| Automated? \| Test case ID \| Automated test name \| Evidence produced`, with every requirement assigned to the lowest layer that can actually prove it and case design approached adversarially (assume broken, not assume working) via the `test-designer` agent; for regulated changes, explicit added rows for audit-event, server-side authorisation, and signature/approval-binding tests, plus tester name/timestamp/method for any Tier 3 manual result; `Evidence produced` must name a real artifact per the evidence profile declared in `.evidence/context/compliance.md`; a coverage-is-interpreted-not-generated policy stating coverage is read from the project's own tooling, never gates a merge, and needs a higher bar on regulated paths; functional (requirement) coverage reported with uncovered `REQ-` IDs named; plans within `.evidence/context/test-strategy.md` when present and route each test type to its owning skill; entry criteria before a cycle and a test summary report (`templates/test-summary-report.md`) after it, go/no-go signed by a named human, never the agent. |
| `traceability-ids` | Use whenever a branch is created, a commit is written, a PR is opened, a test case is authored, or a traceability matrix is produced — and whenever anyone asks how a change is traced. Never produce any of these without the identifier. | Enforcement of the tracker-issue-key anchor across every artifact (branch, commit, PR title, `intent.md`/`spec.md`/`plan.md` header, requirement ID, manual/automated test tags, test run name, traceability matrix row); for cross-repo changes, the `PARENT/CHILD` key convention. |
| `testrail-authoring` | Use when manual test cases are needed for a change, when someone asks for test cases to be written or updated, when a regression suite needs extending, and when a release test run is prepared. Read the tool's field requirements from the profile first. | Manual test cases written into the team's test management system (or, if the write permission isn't recorded in the toolchain profile, as a reviewable file instead) — title, preconditions, one-action-per-step with expected results, tracker key and `REQ-` ID in the traceability fields, priority from the risk tier — plus the case IDs written back onto the tracker issue. |
| `test-automation` | Use when automated tests are written or fixed, when a manual case is automated, when a test is flaky, and when someone asks how test results reach the test management system. Read the framework from the repository profile — never assume one. | Automated tests tagged with the tracker key and, where applicable, the manual case ID they automate; a flake policy outcome (quarantine within one working day, time-boxed, never hidden with a retry); a decision on whether the pipeline (preferred) or the session posts results to the test management system; flake detection in nightly runs (pass and fail on the same commit recorded as flaky, never as passed), with flake rate tracked weekly. |
| `continuous-testing` | Use when designing or changing a pipeline, when someone asks what runs when, or when a stage is slow or noisy. Read the CI system and environments from the repository profile. | A stage design table (Pre-commit / Commit / Pull request / Merge / Deploy-to-test / Nightly / Pre-release / Post-deploy) naming trigger, checks, whether it blocks, and evidence produced, distinguishing what blocks a merge from what merely informs the reviewer; a rollback-rehearsal record; placement of each specialised test type (static analysis, security scanning, DAST, fuzzing, E2E matrix, visual, accessibility, load/stress/soak) by stage, with the test summary report as pre-release evidence. |
| `e2e-ui-testing` | Use when asked to write, fix or speed up E2E or UI tests, or add cross-browser or visual regression tests. Read the tool from the profile. | Thin critical-journey E2E suites: role/label locators, condition-based waits, API-seeded data and per-role saved auth, failure artifacts named for the traceability chain, sharding, a browser/device matrix from the profile, reviewed visual baselines, localisation checks; tool-specific `references/` (Playwright, Selenium, Cypress) loaded only when the profile names that tool. |
| `accessibility-testing` | Use on accessibility, a11y, WCAG, Section 508, EN 301 549, screen readers, keyboard navigation, colour contrast, axe or Lighthouse scores, a VPAT or conformance report. Read the target and tools from the profile — never assume them. | Automated scans at component and journey level plus a recorded manual checklist (keyboard, screen reader, zoom/reflow, contrast, motion, forms, target size) against the conformance target in the profile (`[ASK]` if absent); never a conformance claim from automation alone. |
| `performance-testing` | Use on load testing, "can this handle N users", requests per second, latency or throughput requirements, a performance regression, or a slow endpoint to prove fixed. Read the tool (k6, JMeter, Gatling, Locust or other) from the profile — never assume one. | Load/stress/soak/spike/capacity designs against percentile-plus-error-rate targets that must already be in `spec.md` (a missing target is a spec defect); a workload model, stated environment-parity gap, thresholds fixed before the run, recorded baselines, stress-recovery and soak-trend findings. |
| `security-testing` | Use on vulnerability scans, CVE or dependency alerts, OWASP ZAP/Burp, fuzzing, pen-test prep or retest, or a request to suppress or accept a security finding. Read tools and policy from the profile. | Stage placement for SCA, secret, container/IaC scanning, DAST, fuzzing and pen testing; active testing only against profile-named non-production targets; one findings policy — context-adjusted severity, fix time from the profile, baseline vs new, suppressions with reason, owner, approver and expiry. |
| `static-analysis` | Use when someone sets up or changes a linter, formatter, type checker, SonarQube/Semgrep/CodeQL, wants to disable or relax a rule, adds an eslint/noqa/nolint suppression, or asks why a static check fails. Read tools from the profile — never assume them. | Stage placement per category, a committed baseline that may only shrink with new-code-clean gating, narrow reasoned suppressions, and rule-set changes as their own reviewed change — never a rule disabled to pass a failing PR. |

## `plugins/evidence-compliance`

| Skill | Triggers on | Produces |
| --- | --- | --- |
| `regulatory-controls` | Use when work touches a regulated record, audit trail, access control, retention, consent, personal, payment or health data, or record export, and whenever someone names a framework, an inspection or a certification. | A controls table per applicable framework: `Control \| Verdict (Met / Not met / N/A) \| Evidence`, each verdict backed by a pointer (file/line, test name, audit event, config value), plus a baseline-controls pass (attribution, time integrity, audit completeness, access control, record integrity, data minimisation, retention/deletion) applied regardless of framework. |
| `evidence-package` | Use when a change is merged, when a validation or evidence package is assembled for a release or audit, when someone mentions traceability, revalidation or evidence for a customer, and whenever a control is claimed without a pointer behind it. | A change-impact assessment, append-safe traceability rows in `validation/traceability.csv`, a re-verification call (none/partial/full, justified against risk tier), and a customer-facing note where relevant — derived from the artifact chain, not assembled from scratch; a `NO COVERAGE` row for any requirement with no covering test. |

## `plugins/evidence-integrations`

| Skill | Triggers on | Produces |
| --- | --- | --- |
| `integration-change` | Use at design time when anything "calls a third-party", "integrates with" or uses a "vendor API" or named provider, when a partner announces a change, and when someone asks to remove or clean up an integration that looks unused. Runs alongside secure-api-review. | A `spec.md` integration section answering the direction/ownership, data, trust, availability/failure and operability questions, plus a runbook entry (how to tell it's broken, how to fail over, partner contact, how to replay lost work); flags a regulated-record crossing as requiring its own audit entry of what left, when, to whom, under whose authority. |
| `contract-testing` | Use when an integration is added or changed, a partner ships a new API version, or a spec relies on external behaviour. Trigger when someone proposes updating a contract, fixture or stub to match a partner's new response so a failing contract test passes. Never rely on shared staging as the only proof. | Consumer contract tests run every commit against a stub generated from a recorded contract (never hand-written from docs), schema validation on the inbound boundary, provider verification against a partner-published contract where supported, and a scheduled sandbox smoke test; explicit failure-path and idempotency test coverage. |

---

## Known trigger overlaps

These are pairs of skills that the source explicitly documents as firing together by
design. Skills that merely cover related topics aren't listed.

- **`integration-change` alongside `secure-api-review`.** The `integration-change`
  description ends "Runs alongside secure-api-review." Security review covers the
  attack surface. Integration review covers availability, idempotency and the
  compliance boundary. Neither replaces the other.

- **`spec-and-design` and `risk-tiering` on direct design requests.**
  `spec-and-design`'s description triggers on "design the schema", "design the data
  model", "design the API" and similar. Since v2, `risk-tiering`'s description no
  longer lists those phrases; it triggers at the start of every intent, spec and plan
  instead. The gate engine now covers the gap: `evidence change start` requires
  `--tier`, and policy tier floors deny edits below the floor.

- **`compliance-discovery` alongside `stack-discovery`.** Both are onboarding-time
  discovery skills, and `compliance-discovery`'s body says it "runs once per project
  alongside stack discovery". They write separate profile files, and neither
  substitutes for the other.

Beyond these pairings, several skills instruct their own body text
to *apply* another skill as part of producing their output (for example,
`spec-and-design` applying `regulatory-controls`, `evidence-package`,
`secure-api-review`, `integration-change` and `traceability-ids`; `schema-migration`
and `secure-api-review` both applying `agent-trust-boundaries`). Those are
sequential composition — one skill's procedure calls for another's checklist — rather
than two skills independently triggering on the same phrase, so they are not listed
above as overlaps.

---

## Agents

There are 11 agents across the plugins. Agents have no trigger description in the
same sense as skills: the main session dispatches them, as the skills and commands
tell it to. Every agent except `docs-writer` is on the engine's `read_only_agents`
list, so a write by one of them is denied by `agent_type` even if its tools would
allow it.

| Agent | Plugin | Tools | Role |
| --- | --- | --- | --- |
| `stack-surveyor` | evidence-discovery | Read, Grep, Glob, Bash | Read-only repository survey with evidence and confidence markers |
| `codebase-cartographer` | evidence-sdlc | Read, Grep, Glob (`model: haiku`) | Reports what already exists in an area before anything new is proposed |
| `architect` | evidence-sdlc | Read, Grep, Glob | Checks a design against the ADRs in `.evidence/decisions/` and drafts a new or superseding ADR from `templates/adr.md`. Returns the text; the main session writes it |
| `security-reviewer` | evidence-sdlc | Read, Grep, Glob, Bash | Security review of a diff: tenant isolation, object-level authorisation, signature integrity. Reports every Critical/High finding regardless of confidence. **Required before push or PR at Tier 2 and 3** |
| `code-reviewer` | evidence-sdlc | Read, Grep, Glob, Bash | Runs the four `REVIEW.md` passes (bugs, security, compliance, conformance to spec and plan). **Required before push or PR at Tier 3** |
| `verifier` | evidence-sdlc | Bash, Read, Grep | Runs the build, the tests and the app, and reports whether the change works. **Required before push or PR at every tier.** No longer pinned to Haiku |
| `release-manager` | evidence-sdlc | Read, Grep, Glob | Release readiness: drafts the test summary report, and checks rollback evidence, open defects and approvals. Never signs |
| `docs-writer` | evidence-sdlc | Read, Grep, Glob, Edit, Write | Updates docs, changelog and release notes to match the merged behaviour. The only agent that can write, and it is limited to documentation paths |
| `test-designer` | evidence-quality | Read, Grep, Glob | Derives test cases and layers from a spec, including empty-state, concurrency, boundary, property-based and regulated-record cases |
| `flake-triage` | evidence-quality | Read, Grep, Glob, Bash | Classifies an intermittent failure as a real defect, a test defect, or environmental |
| `compliance-reviewer` | evidence-compliance | Read, Grep, Glob, Bash | Controls and validation pass over a diff or spec, against the control sets that apply |

An org or repo policy can change which agents a tier requires (`required_agents`; see
[policy-reference.md](policy-reference.md)).

## Slash commands

All five are in `evidence-sdlc`: `/evidence-sdlc:start`, `/evidence-sdlc:status`,
`/evidence-sdlc:approve` (human-only: `disable-model-invocation`, and the hook does the
recording), `/evidence-sdlc:gaps` and `/evidence-sdlc:release-report`.
