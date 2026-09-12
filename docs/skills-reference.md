# Skills reference

This is the full trigger-phrase reference for every skill shipped across Evidence
Chain's five plugins: exact wording pulled from each skill's own `SKILL.md`
frontmatter `description`, what it produces (from the body), and which explicit
alongside/overlap relationships are documented in the source. See
[`README.md`](../README.md) for the plugin-level narrative — what each plugin is for
and how they fit together — and for the discovery-writes-a-profile / gates model this
reference assumes throughout. Where a description does not state a literal trigger
phrase, that is noted rather than invented.

Two agents that are *not* skills (`compliance-reviewer` in evidence-compliance,
`stack-surveyor`/`codebase-cartographer`/`verifier`/`security-reviewer` etc. in
evidence-discovery and evidence-sdlc, `test-designer`/`flake-triage` in
evidence-quality) are out of scope for this table — they have no `SKILL.md`
frontmatter description to quote and are covered in `README.md`'s per-plugin tables
instead.

---

## `plugins/evidence-discovery`

| Skill | Triggers on | Produces |
| --- | --- | --- |
| `stack-discovery` | "Use this the first time any session runs in a repo, whenever `.evidence/context/` is missing or stale, and before any spec or plan that depends on stack facts." Also: "Trigger on any question about languages, runtimes, frameworks, datastores, build tooling or deployment targets, however it is phrased — including 'what stack', 'what framework', 'what language', 'what database', 'what does this repo use', 'what's the tech stack', 'what are we running on', casual variants of these, and follow-up questions about any of them — even when CLAUDE.md, a README, an architecture document, or another document appears to already answer it." | `.evidence/context/stack.md` and `.evidence/context/deployment.md`, written from templates, each line marked `[confirmed]`/`[inferred]`/`[ASK]`; finishes by presenting the `[ASK]` list as numbered questions and blocks any spec/plan on an unresolved one. |
| `toolchain-discovery` | "Use this during repository onboarding, whenever a workflow needs a tool the session cannot currently reach, whenever someone asks whether Claude can talk to a given system, and before designing any cross-tool automation." Also: "Trigger on plain questions too: 'can you access our Jira/GitHub/CI', 'are we connected to X', 'what's our tracker', 'do we have a test management tool', 'what CI do we use' — even when a README or onboarding doc appears to already say." | `.evidence/context/toolchain.md` (per tool: use, connectivity class — `MCP-official`/`MCP-community`/`MCP-internal`/`CLI`/`REST-scripted`/`Manual`, credential source, scope, owner, unreachable-fallback) and `.evidence/adapter.yml` (generated from `.evidence/adapter.example.yml`'s field list: `requirements_source`, `spec_glob`, `requirement_pattern`, `tracker_pattern`, `test_dir_segments`, `artifact_chain`, `test_results_location`). |
| `design-system-discovery` | "Use this during repository onboarding, before any UI or frontend planning, whenever a new component is proposed, and whenever someone asks what the design conventions are." Also: "Trigger on plain questions too: 'what component library do we use', 'what UI kit', 'what CSS framework', 'do we have a design system' — even when a README or style guide appears to already answer it." | `.evidence/context/design-system.md` — source of truth (package vs. in-repo vs. design-tool-only), tokens and where defined, conventions, accessibility baseline; sets the standing rule that a new component needs written justification in `plan.md`. |
| `compliance-discovery` | "Use this at repository onboarding alongside stack discovery, whenever someone asks what regulations apply, whenever a new market or customer segment is entered, and before any spec that could touch a regulated record." Also: "Trigger on plain questions too: 'are we HIPAA/SOC2/GDPR/PCI compliant', 'is this regulated', 'what compliance requirements apply to us', 'do we need to worry about [a named regulation]' — even when a README or policy doc appears to already answer it." | `.evidence/context/compliance.md` — industry/markets, jurisdictions, each applicable framework with its role (legal/contractual/certified/claimed) and named owner, regulated-record definition, "none apply" recorded as a real answer when true; each entry marked `[confirmed]`/`[inferred]`/`[ASK]`. |
| `document-ingestion` | "Use this at the start of any adoption where prior documentation exists in Word, PDF, spreadsheets or slides, whenever someone asks how existing procedures fit into this process, and whenever a change touches a requirement that only exists in a legacy document." No plain-question trigger list is given for this skill. | Markdown working copies of controlled documents (SOPs, protocols, specs, audit reports), each carrying a header naming source document ID/version/system-of-record and stating "the controlled document is the record"; a recorded source-of-truth decision per document class (repo-authoritative / legacy-authoritative / linkage-only) written into `.evidence/context/`. |

## `plugins/evidence-sdlc`

| Skill | Triggers on | Produces |
| --- | --- | --- |
| `intent-capture` | "Use this whenever anyone — product, support, UX, QA, sales engineering, or an on-call engineer — starts describing something they want built, changed, or fixed, even if they never say the word 'intent', 'requirement' or 'story'. If someone is about to describe work in prose, capture it here first." | `intent/<yyyy-mm-dd>-<slug>/intent.md` from the template — problem, affected users, regulated-record and evidence-impact answers, data classification, measurable "better," explicit out-of-scope, committed to git with author/timestamp. |
| `spec-and-design` | "Use this whenever an intent has been accepted, whenever someone asks for a design, a solution approach, an API design, or a technical approach document, and before any implementation planning begins." Also: "Also trigger on direct design requests that use no process vocabulary at all — 'design the schema', 'design the data model', 'design the API', 'how should we structure...', 'what should the table look like', 'model this', 'what fields do we need', 'sketch the design' — those are still design work and still need a spec, not just an answer." | `spec.md` next to `intent.md` — `REQ-<area>-<nn>` requirements traced to `intent.md`, a regulatory control table per applicable framework, evidence impact, security design notes, data classification/residency, UX states, and an "areas of concern" section routed to named owners; unverified claims marked `[NEEDS VERIFICATION]`. |
| `codebase-grounded-planning` | "Use this at the start of every implementation session, whenever someone says 'plan this', 'how would we build this', 'break this down', or asks for tasks, subtasks, or a work breakdown, and whenever a session is about to start editing code without an approved plan on disk." | `plan.md` (or `plan/<TRACKER-KEY>.md` for concurrent sessions) from the template — real file paths only, a "Files claimed" section, a test-plan row per `REQ-` ID (via `test-strategy`), ordered/risk-stated work, committed before implementation begins. |
| `risk-tiering` | "Use this at the start of every intent, spec and plan, whenever someone asks how much process a change needs, whenever a Definition of Ready or Done is being checked, and whenever review is being assigned." Also: "Also trigger on direct design requests with no process vocabulary at all — 'design the schema', 'design the data model', 'design the API', 'how should we structure...', 'what should the table look like', 'model this', 'what fields do we need', 'sketch the design' — a tier must be stated before that design work proceeds." | A stated Tier 1/2/3 classification with a one-line reason, and the matching tiered Definition of Ready and Definition of Done for the change. |
| `secure-api-review` | "Use this whenever code creates or modifies an API route, touches authentication, authorization, tenancy, tokens, key material, file upload/download, webhooks, or third-party calls; whenever an OpenAPI spec is generated; and whenever anyone asks for a security review, threat model, or pen-test prep." | A findings table: `Severity (Critical/High/Medium/Nit) \| Location \| What \| Why it matters here \| Suggested fix`, scoped deliberately to tenancy, regulated-record definition, audit-event requirements, residency rules and supply-chain policy — not the generic vulnerability classes a scanner already covers. |
| `agent-trust-boundaries` | "Use this whenever designing or reviewing anything that feeds external content to a model, whenever an agent is given a tool that reads user-supplied data, and on every review of an agent embedded in the product itself." No plain-question trigger list is given for this skill. | A boundary-by-boundary control check (structural separation, least tool surface, no standing credentials, deterministic authorisation, output-as-untrusted, agent action audit, blast-radius statement) and, for an in-product agent, a flag that it needs its own validation/risk-assessment/regulatory mapping as "a regulated computerised system in its own right." |
| `legacy-characterization` | "Use this before any modification to a module with thin test coverage, before any refactor or framework upgrade, whenever someone says a piece of code is scary, risky, legacy, or nobody understands it, and as the first workstream when onboarding an old repository into the AI-SDLC." | Characterization tests (captured current behaviour, not intended behaviour) committed on their own before any behavioural change, with suspected-bug behaviour marked `// CHARACTERIZATION: current behaviour, believed incorrect`; for regulated modules, explicit assertions on which audit events fire, in what order, with which fields. |
| `root-cause-analysis` | "Use this whenever someone says 'this is broken', 'why is this failing', 'debug this', 'investigate this error', 'production issue', 'it works locally but not in X', pastes a stack trace or error log, or reports any unexpected behaviour." | A failing test committed alone (proving the bug) before any fix, then a findings table: `Symptom \| Trigger \| Root cause \| Evidence for that conclusion \| Assumptions \| Edge cases this also affects \| Proposed fix \| Test that proves it`; for regulated records, a pointer to `governance/deviation-capa-runbook.md`. |
| `schema-migration` | "Use whenever anyone says 'migration', 'alter the schema', 'add a column', 'change the data model', 'backfill', 'rename a field', 'drop a table', 'reindex', and on any edit under a migrations directory." | A migration proposal stating, in order: which expand-contract phase this is, the backward-compatibility argument for that phase, the backfill verification plan (count check + sample correctness + zero-remaining-rows query, or "no backfill needed" with why), the rollback plan (tested, or explicitly irreversible with why), regulated-record checks (or "not a regulated table" with why), and the risk tier. |

## `plugins/evidence-quality`

| Skill | Triggers on | Produces |
| --- | --- | --- |
| `test-strategy` | "Use this during spec and plan, whenever someone asks how something will be tested, whenever a requirement has no named test, and before any test case or automated test is written." | The test-plan table for `plan.md`: `REQ ID \| Layer \| Automated? \| Test case ID \| Automated test name \| Evidence produced`, with every requirement assigned to the lowest layer that can actually prove it; for regulated changes, explicit added rows for audit-event, server-side authorisation, and signature/approval-binding tests. |
| `traceability-ids` | "Use this whenever a branch is created, a commit is written, a PR is opened, a test case is authored, or a traceability matrix is produced — and whenever anyone asks how a change is traced." | Enforcement of the tracker-issue-key anchor across every artifact (branch, commit, PR title, `intent.md`/`spec.md`/`plan.md` header, requirement ID, manual/automated test tags, test run name, traceability matrix row); for cross-repo changes, the `PARENT/CHILD` key convention. |
| `testrail-authoring` | "Use this whenever manual test cases are needed for a change, whenever someone asks for test cases to be written or updated, when a regression suite needs extending, and when a release test run is being prepared." | Manual test cases written into the team's test management system (or, if the write permission isn't recorded in the toolchain profile, as a reviewable file instead) — title, preconditions, one-action-per-step with expected results, tracker key and `REQ-` ID in the traceability fields, priority from the risk tier — plus the case IDs written back onto the tracker issue. |
| `test-automation` | "Use this whenever automated tests are being written or repaired, whenever a manual case is being automated, whenever a test is flaky, and whenever someone asks how test results reach the test management system." | Automated tests tagged with the tracker key and, where applicable, the manual case ID they automate; a flake policy outcome (quarantine within one working day, time-boxed, never hidden with a retry); a decision on whether the pipeline (preferred) or the session posts results to the test management system. |
| `continuous-testing` | "Use this when designing or changing a pipeline, when someone asks what runs when, when a stage is slow or noisy, and when release evidence needs to be produced." | A stage design table (Pre-commit / Commit / Pull request / Merge / Deploy-to-test / Nightly / Pre-release / Post-deploy) naming trigger, checks, whether it blocks, and evidence produced, distinguishing what blocks a merge from what merely informs the reviewer; a rollback-rehearsal record. |

## `plugins/evidence-compliance`

| Skill | Triggers on | Produces |
| --- | --- | --- |
| `regulatory-controls` | "Use this whenever work touches a regulated record, audit trail, authentication, access control, retention, consent, personal data, payment data, health data, or record export — and whenever anyone mentions compliance, an audit, an inspection, a certification, or a named framework." | A controls table per applicable framework: `Control \| Verdict (Met / Not met / N/A) \| Evidence`, each verdict backed by a pointer (file/line, test name, audit event, config value), plus a baseline-controls pass (attribution, time integrity, audit completeness, access control, record integrity, data minimisation, retention/deletion) applied regardless of framework. |
| `evidence-package` | "Use this whenever a change is specced or merged, whenever a release is prepared, whenever anyone mentions traceability, revalidation, an audit, a certification, or evidence for a customer, and whenever a control is claimed without a pointer behind it." | A change-impact assessment, append-safe traceability rows in `validation/traceability.csv`, a re-verification call (none/partial/full, justified against risk tier), and a customer-facing note where relevant — derived from the artifact chain, not assembled from scratch; a `NO COVERAGE` row for any requirement with no covering test. |

## `plugins/evidence-integrations`

| Skill | Triggers on | Produces |
| --- | --- | --- |
| `integration-change` | "Use whenever an integration is added, versioned, deprecated or debugged, whenever a partner announces a change, and whenever a spec proposes calling or being called by anything outside the platform." Also: "Trigger on plain-language phrasings too: 'calls a third-party', 'calls an external API', 'integrates with', 'webhook', 'provider', 'vendor API', 'SDK for', and any named external service (an e-sign provider, a payment processor, a mapping service, and so on). This applies at DESIGN time, the first time such a call is proposed — not only at review time — and it runs ALONGSIDE `secure-api-review` rather than being replaced by it: security covers the attack surface, this skill covers availability, idempotency and the compliance boundary." | A `spec.md` integration section answering the direction/ownership, data, trust, availability/failure and operability questions, plus a runbook entry (how to tell it's broken, how to fail over, partner contact, how to replay lost work); flags a regulated-record crossing as requiring its own audit entry of what left, when, to whom, under whose authority. |
| `contract-testing` | "Use whenever an integration is added or changed, whenever a partner publishes a new API version, whenever an integration incident is investigated, and whenever a spec relies on an external system behaving a particular way." | Consumer contract tests run every commit against a stub generated from a recorded contract (never hand-written from docs), schema validation on the inbound boundary, provider verification against a partner-published contract where supported, and a scheduled sandbox smoke test; explicit failure-path and idempotency test coverage. |

---

## Known trigger overlaps

These are skill pairs the source explicitly documents as firing together by design,
not skills that merely happen to be topically related:

- **`integration-change` alongside `secure-api-review`.** `integration-change`'s
  description states outright that it "runs ALONGSIDE `secure-api-review` rather than
  being replaced by it: security covers the attack surface, this skill covers
  availability, idempotency and the compliance boundary." Both fire on the same
  trigger — a new or changed external API call — and neither supersedes the other.

- **`risk-tiering` alongside `spec-and-design` on direct design asks.** Both skills'
  descriptions independently list the identical set of no-process-vocabulary design
  phrases — "design the schema", "design the data model", "design the API", "how
  should we structure...", "what should the table look like", "model this", "what
  fields do we need", "sketch the design." `spec-and-design` says these "are still
  design work and still need a spec, not just an answer"; `risk-tiering` says "a tier
  must be stated before that design work proceeds." The two are meant to fire
  together on that phrasing: state the tier, then produce the spec — neither replaces
  the other.

- **`compliance-discovery` alongside `stack-discovery`.** `compliance-discovery`'s
  description says to "Use this at repository onboarding alongside stack discovery,"
  and its body repeats "This runs once per project alongside stack discovery." Both
  are onboarding-time discovery skills that write separate profile files
  (`compliance.md`, `stack.md`/`deployment.md`) consumed by everything downstream;
  neither is a substitute for the other.

Beyond these three documented pairings, several skills instruct their own body text
to *apply* another skill as part of producing their output (for example,
`spec-and-design` applying `regulatory-controls`, `evidence-package`,
`secure-api-review`, `integration-change` and `traceability-ids`; `schema-migration`
and `secure-api-review` both applying `agent-trust-boundaries`). Those are
sequential composition — one skill's procedure calls for another's checklist — rather
than two skills independently triggering on the same phrase, so they are not listed
above as overlaps.
