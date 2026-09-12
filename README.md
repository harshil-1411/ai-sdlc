# Evidence Chain

**An AI-native SDLC control plane for teams that have to prove what they shipped.**

Claude Code plugins that put an agent inside your whole development lifecycle while
keeping the controls a regulated, audited, or safety-relevant product needs — planning
gates, traceability, test discipline, security review, and a validation-evidence chain
that falls out of the process instead of being assembled at release time.

> **This is not regulatory, legal or compliance advice.** Read [DISCLAIMER.md](DISCLAIMER.md)
> before using any of it. Nothing here makes anything compliant; every gate ends at a
> named human, deliberately.

---

## The problem it addresses

Code stopped being the bottleneck. The steps either side of it did not move.

Once agents write most of the diff, two things break at once. Review capacity — reading
every line made sense when a person wrote every line. And evidence — the faster you
ship, the more expensive it gets to reconstruct *what was required, what was built, what
proved it, and who approved it.*

Going faster without addressing those just moves the queue to QA and security, and in a
regulated shop it produces a human approval gate that has quietly become fiction. An
auditor probing an approval nobody read is a worse outcome than not using AI at all.

Evidence Chain's answer: **each stage ends by committing an artifact the next stage
reads, and the controls run at the moment the agent acts.** The chain of commits is then
the audit trail.

```mermaid
flowchart LR
    A["1 · Plan<br/>intent.md"] --> B["2 · Design<br/>spec.md"]
    B --> C["3 · Build<br/>plan.md"]
    C --> D["4 · Test<br/>diff + tests"]
    D --> E["5 · Deploy<br/>PR + findings"]
    E --> F["6 · Maintain<br/>release + evidence"]
    F -. "incident · anomaly<br/>customer finding" .-> A

    style A fill:#e8f0fe,stroke:#4a6fa5
    style B fill:#e8f0fe,stroke:#4a6fa5
    style C fill:#e8f0fe,stroke:#4a6fa5
    style D fill:#e8f0fe,stroke:#4a6fa5
    style E fill:#e8f0fe,stroke:#4a6fa5
    style F fill:#e8f0fe,stroke:#4a6fa5
```

### What each stage produces, and who owns it

```mermaid
flowchart TD
    subgraph S1["1 · PLAN — originator (anyone)"]
        I["intent.md<br/>· problem, affected users<br/>· constraints, regulatory impact<br/>· open questions"]
    end
    subgraph S2["2 · DESIGN — product owner reviews, does not write"]
        SP["spec.md<br/>· REQ- IDs, design, diagrams<br/>· control tables<br/>· areas of concern"]
    end
    subgraph S3["3 · BUILD — engineer"]
        PL["plan.md<br/>· real file paths<br/>· order of work, risks<br/>· test plan rows"]
        DF["diff + tests<br/>· tagged with tracker key<br/>· tagged with test case IDs"]
    end
    subgraph S4["4 · TEST — QA owns the suite"]
        TC["test cases<br/>· in the test management system"]
        TR["test runs<br/>· results posted by the pipeline"]
    end
    subgraph S5["5 · DEPLOY — code owner approves"]
        PR["PR + review findings<br/>· bugs, security, compliance<br/>· conformance to plan.md"]
    end
    subgraph S6["6 · MAINTAIN — service owner"]
        EV["release record + evidence export<br/>· traceability matrix<br/>· impact assessment"]
    end

    I --> SP --> PL --> DF
    SP -.-> TC
    DF --> TR --> PR --> EV
    EV -. "finding becomes<br/>a new intent" .-> I

    style S1 fill:#f7f9fc,stroke:#c3d0e0
    style S2 fill:#f7f9fc,stroke:#c3d0e0
    style S3 fill:#f7f9fc,stroke:#c3d0e0
    style S4 fill:#f7f9fc,stroke:#c3d0e0
    style S5 fill:#f7f9fc,stroke:#c3d0e0
    style S6 fill:#f7f9fc,stroke:#c3d0e0
```

Every arrow is a commit. The chain of commits is the audit trail: who asked for what,
what the agent produced, what proved it, and who approved it.

## Two design commitments

**1. It does not know your stack, and never guesses.**

No skill hardcodes a language, framework, datastore, or deployment target. Instead
`evidence-discovery` runs first in each repository and writes a profile to
`.evidence/context/`. Every other skill reads that profile.

Discovery has one standing rule: **evidence, then question, never guess.**

```mermaid
flowchart TD
    R["Read the repository"] --> Q{"Can this be established<br/>from a file I read?"}
    Q -- yes --> C["[confirmed]<br/>— cite the file"]
    Q -- "strong signal,<br/>not declarative" --> N["[inferred]<br/>— state the evidence"]
    Q -- no --> A["[ASK]<br/>— numbered question<br/>for a named human"]
    C --> P[".evidence/context/"]
    N --> P
    A --> H["Human answers<br/>— recorded with name and date"] --> P
    P --> G{"Unresolved [ASK] in an area<br/>this change depends on?"}
    G -- yes --> B["BLOCKED<br/>— ask before speccing"]
    G -- no --> OK["Proceed to spec"]

    style A fill:#fdf0e3,stroke:#c98b3a
    style B fill:#fbe6e6,stroke:#c05050
    style OK fill:#e7f5ec,stroke:#4a9163
```

The profile files it writes:

| File | Holds |
| --- | --- |
| `stack.md` | Languages, frameworks, data layer, build/test/lint commands, VCS conventions |
| `deployment.md` | IaC, environments, regions, residency, pipelines, rollback |
| `toolchain.md` | Every tool, how the agent reaches it, credentials, scope, read vs write |
| `design-system.md` | Component source of truth, tokens, conventions, accessibility baseline |
| `compliance.md` | Industry, jurisdictions, applicable frameworks, regulated record types |

Confidently wrong is the expensive failure mode, and a framework that assumes a stack —
or a regulation — will be confidently wrong in half your repositories.

**2. Skills advise; hooks enforce.**

A skill makes an agent very likely to apply a policy while writing code. Nothing forces
compliance. A hook runs on every matching action, for everyone, and can block.

So: write a skill for everything, and put a hook behind any policy that must hold
without exception. Hooks on everything creates prompt fatigue and people route around
them. Skills on everything means your controls are a suggestion. Getting this balance
wrong in either direction is the main way these rollouts fail.

---

## Install

```
/plugin marketplace add <your-org>/evidence-chain
/plugin install evidence-discovery@evidence-chain
/plugin install evidence-sdlc@evidence-chain
```

Then run discovery in the repository you want to onboard, and answer its questions. Add
`evidence-quality`, `evidence-compliance` and `evidence-integrations` as they become
relevant.

Read every hook script before installing. They run on your machine with your
permissions — that is the point, and it is also the risk. See [SECURITY.md](SECURITY.md).

`cli/evidence` needs no install step of its own — it's a single Python 3 script,
standard library only. `python3 cli/evidence doctor` is a reasonable first command to
run in any repository, installed or not.

## What's in here

```
.claude-plugin/marketplace.json   Marketplace manifest
.mcp.json.example                 Connector template, keyed to the toolchain profile
managed-settings.json             Platform-owned policy engineers cannot override
pipeline.example.yml              CI + continuous testing stage design
.evidence/adapter.example.yml     Where THIS repo's traceability chain lives — copy
                                  the matching preset to .evidence/adapter.yml
cli/evidence                      doctor / scan / gaps / export — see cli/README.md
cli/REVIEW-BRIEF.md               Structural walkthrough + reviewer checklist for
                                  the CLI itself — read before trusting its output
cli/tests/                        The CLI's own regression fixtures
intent/                           This repo's own artifact chain, dogfooded — real
                                  intent.md/spec.md pairs, including a retrospective
                                  one written for the CLI after the fact
validation/traceability.csv       A real, populated sample export — not the empty
                                  template; see docs/external-review-packet.md
docs/                             toolchain-connectivity.md — what connects how
                                  third-party-tooling.md — what to adopt, and what
                                  quietly disables the controls
                                  external-review-packet.md — the traceability export,
                                  explained for a QA/RA lead who has never seen this
governance/                       The documents an auditor asks for, including
                                  human-capability.md — the reviewer-judgement risk

plugins/
  evidence-discovery/     RUN FIRST. Establishes facts; never assumes a stack.
    stack-discovery             Languages, frameworks, data, build/test/run commands
    toolchain-discovery         Which tools, and whether you can reach them
    design-system-discovery     Component source of truth, tokens, conventions
    compliance-discovery        Industry, jurisdictions, frameworks — asked, not inferred
    document-ingestion          Existing SOPs and protocols into the chain, safely
    stack-surveyor              Read-only survey with evidence and confidence markers

  evidence-sdlc/          Stack-agnostic. The core loop.
    intent-capture              Front door for every team, not just engineering
    spec-and-design             Requirements + design in one pass, policy applied live
    codebase-grounded-planning  Plans against the repo you actually have
    risk-tiering                Ceremony scales with risk; tiered DoR and DoD
    secure-api-review           What a generic scanner can't know: tenancy, regulated
                                records, audit requirements, residency
    schema-migration            Expand-contract, backfill verification, tested
                                rollback, regulated-record integrity on migrations
    agent-trust-boundaries      Untrusted content is data, never instruction
    legacy-characterization     Pin down old code before touching it
    root-cause-analysis         Trace a defect to its actual cause before fixing it
    agents/                     cartographer, verifier, security-reviewer
    hooks/ scripts/             The deterministic gates, plus preflight.sh
                                (checks jq/scripts/hooks.json health at session start)
                                and tests/ (regression suite for the gate scripts)
    templates/                  intent / spec / plan / REVIEW / DoR-DoD / CLAUDE.md
                                (spec.md's own Diagrams section now carries the
                                guidance the former architecture-diagrams skill gave)

  evidence-quality/       Testing and the traceability chain.
    traceability-ids            One key linking tracker → case → commit → evidence
    test-strategy               Which layer proves which requirement
    testrail-authoring          Manual cases in the tool's required format, linked back
    test-automation             Framework-agnostic discipline, tagging, flake policy
    continuous-testing          What runs when, what blocks, what is evidence
    agents/                     test-designer, flake-triage

  evidence-compliance/    For regulated records.
    regulatory-controls             Framework-agnostic control checks, with shipped control sets
    evidence-package          Derives the deliverables you owe from the artifact chain
    compliance-reviewer         Controls + validation pass over a diff

  evidence-integrations/  Anything crossing the platform boundary.
    integration-change          Trust + availability + compliance boundary at once
    contract-testing            Catch partner drift in the pipeline, not in production

examples/
  skills/decision-council/  Optional, not installed by default — multi-perspective
                            pressure test for one-way doors. See examples/README.md.
```

## How the plugins fit together

```mermaid
flowchart TD
    D["evidence-discovery<br/>— runs first, per repo"] ==> CTX[(".evidence/context/<br/>stack · deployment · toolchain<br/>design-system · compliance")]

    CTX --> S["evidence-sdlc<br/>· intent → spec → plan<br/>· risk tiering, council<br/>· the deterministic gates"]
    CTX --> Q["evidence-quality<br/>· traceability, test strategy<br/>· cases, automation, CI"]
    CTX --> C["evidence-compliance<br/>· loads only the control sets<br/>the profile names"]
    CTX --> I["evidence-integrations<br/>· boundary changes<br/>· contract tests"]

    S --> ART[("Committed artifact chain<br/>= the audit trail")]
    Q --> ART
    C --> ART
    I --> ART

    style D fill:#e8f0fe,stroke:#4a6fa5
    style CTX fill:#fdf6e3,stroke:#b39b52
    style ART fill:#e7f5ec,stroke:#4a9163
```

Nothing downstream of discovery hardcodes a stack, a toolchain, or a regulation. They
all read the profile.

## The gates

| Gate | Enforces |
| --- | --- |
| `require-repo-profile` | Every session knows the stack — or knows that it doesn't |
| `gate-plan-exists` | No source edit without an approved `plan.md` (or `plan/<TRACKER-KEY>.md`) on disk |
| `require-issue-key` | No commit without the tracker key. The chain has no gaps |
| `protect-validated-paths` | Change-controlled paths need a change ticket in the environment |
| `block-test-weakening` | An agent fixing a bug cannot edit the test that proves it |
| `block-protected-branch-push` | The agent has no route to main. Segregation of duties, mechanically |
| `production-gate` | The agent may act up to the production gate and not past it |

```mermaid
flowchart TD
    S(["Session starts"]) --> H0["require-repo-profile<br/>— advisory"]
    H0 --> ACT{"Agent acts"}

    ACT -- "Edit / Write" --> H1{"plan.md or plan/&lt;key&gt;.md on disk?"}
    H1 -- no --> D1["DENY<br/>— run planning first"]
    H1 -- yes --> H2{"change-controlled path?"}
    H2 -- "yes, no ticket" --> D2["DENY<br/>— needs a change record"]
    H2 -- otherwise --> H3{"test file, during a fix task?"}
    H3 -- yes --> D3["DENY<br/>— fix the code, not the test"]
    H3 -- no --> ALLOW["ALLOW<br/>+ append to edit log"]

    ACT -- "git commit" --> H4{"tracker key present?"}
    H4 -- no --> D4["DENY<br/>— chain would have a gap"]
    H4 -- yes --> ALLOW

    ACT -- "git push" --> H5{"protected branch?"}
    H5 -- yes --> D5["DENY<br/>— open a PR, a human approves"]
    H5 -- no --> ALLOW

    ACT -- "deploy" --> H6{"production, no<br/>release authorisation?"}
    H6 -- yes --> D6["DENY<br/>— named human authorises"]
    H6 -- no --> ALLOW

    style D1 fill:#fbe6e6,stroke:#c05050
    style D2 fill:#fbe6e6,stroke:#c05050
    style D3 fill:#fbe6e6,stroke:#c05050
    style D4 fill:#fbe6e6,stroke:#c05050
    style D5 fill:#fbe6e6,stroke:#c05050
    style D6 fill:#fbe6e6,stroke:#c05050
    style ALLOW fill:#e7f5ec,stroke:#4a9163
```

## Running parallel sessions safely

The framework originally assumed one session, one `plan.md`, one branch. Parallel
agent sessions in separate worktrees are becoming standard, and two sessions fighting
over one bare `plan.md` — or silently editing the same module without either
cartographer seeing the other's uncommitted work — is how two correct changes produce
one broken merge. A few rules keep that from happening:

- **One tracker key per worktree.** Each concurrent session plans into its own
  `plan/<TRACKER-KEY>.md` (see `codebase-grounded-planning`'s "Concurrent sessions"
  section) rather than the bare `plan.md` every session used to share.
  `gate-plan-exists` accepts both — the namespaced form is required only when more
  than one session might be planning here at once.
- **No shared regulated paths across concurrent sessions.** A change-controlled path
  (`migrations/`, `infra/`, `audit/`, `signing/`, `crypto/`, `validation/`, per
  `protect-validated-paths`) gets one session at a time. Sequence them and say why in
  each plan.
- **Check "Files claimed" before planning.** Every `plan.md`/`plan/<key>.md` has a
  "Files claimed" section. Read the other active plans in this repository (other
  worktrees, other open branches) before writing yours; if a path you need is already
  claimed, stop and sequence instead of proceeding.
- **State merge order up front.** When two plans are known to touch adjacent code,
  name which one merges first in both plans, not just the one that happens to finish
  first.

## Compliance without hardcoding a regulation

`compliance-discovery` establishes which frameworks actually apply and writes them to
`.evidence/context/compliance.md`. `regulatory-controls` then loads only the matching
control sets. Nothing assumes an industry.

```mermaid
flowchart LR
    subgraph ASK["compliance-discovery — asks humans, does not infer"]
        A1["Industry and markets"]
        A2["Jurisdictions"]
        A3["Frameworks + their role<br/>legal, contractual,<br/>certified, claimed"]
        A4["Regulated record types<br/>for this product"]
        A5["Named owner per framework"]
    end
    ASK ==> PROF[("compliance.md")]
    PROF --> LOAD{"regulatory-controls<br/>loads only what applies"}
    LOAD --> R1["21 CFR Part 11"]
    LOAD --> R2["EU GMP Annex 11"]
    LOAD --> R3["IEC 62304 · ISO 13485"]
    LOAD --> R4["SOC 2"]
    LOAD --> R5["HIPAA · PCI DSS · GDPR"]
    LOAD --> R6["your own control set"]
    LOAD --> R0["none apply<br/>— a real, recorded answer"]

    style PROF fill:#fdf6e3,stroke:#b39b52
    style R0 fill:#eeeeee,stroke:#999999
    style R6 fill:#e8f0fe,stroke:#4a6fa5
```

Two things this deliberately gets right. **Applicability is asked, not inferred** — a
repository cannot tell you which markets you sell into or what you committed to
contractually, so every entry carries a person's name and a date. And **the role of each
framework is recorded separately**: a legal obligation, a contractual commitment, a
certification you hold, and a standard you merely claim alignment with are four
different things that are routinely conflated.

Shipped control sets live in
`plugins/evidence-compliance/skills/regulatory-controls/references/`. They are starting
points drafted from public sources, structured for reviewing a diff rather than for
satisfying an auditor. Writing your own is expected — `references/README.md` gives the
shape.

## Traceability

The tracker issue key is the anchor; everything references it.

```mermaid
flowchart TD
    K(["Tracker issue<br/>KEY"])
    K --> RQ["Requirement IDs<br/>REQ-area-nn<br/>(in spec.md)"]
    K --> BR["Branch<br/>type/KEY-slug"]
    BR --> CM["Commits<br/>(every message carries KEY)"]
    CM --> PR["Pull request<br/>(title carries KEY)"]
    RQ --> TC["Manual test cases<br/>(KEY in a case field)"]
    RQ --> AT["Automated tests<br/>(tagged KEY + case ID)"]
    TC --> RUN["Test run<br/>(named KEY + build)"]
    AT --> RUN
    PR --> AP["Approval<br/>(named code owner)"]
    RUN --> MX["Traceability matrix row"]
    AP --> MX
    RQ --> MX

    TC -. "case ID written<br/>back onto the issue" .-> K
    PR -. "PR link written<br/>back onto the issue" .-> K
    RUN -. "results attached<br/>to case and issue" .-> K

    style K fill:#e8f0fe,stroke:#4a6fa5
    style MX fill:#e7f5ec,stroke:#4a9163
```

The dotted arrows are the half people skip. A test case that references the issue while
the issue does not reference the case is a half-chain, and half-chains are what make
audits expensive.

**Two-way linking is the point.** One-way links rot. Creating a test case writes its ID
back onto the issue; a completed run attaches results to both.

## The evidence CLI — testing whether any of this is actually derivable

Every skill above describes how the artifact chain is *supposed* to trace. `cli/evidence`
is the one part of this framework that actually tries to derive it — a small,
dependency-free Python 3 script, no network access, that reads a repository's own
commits, spec files and tests and builds the traceability graph itself, rather than
trusting a description of one.

```
evidence doctor   # preflight: jq on PATH, gate scripts readable, hooks.json sane,
                  # profile presence, unresolved [ASK] count, profile staleness
evidence scan     # build the graph: tracker keys -> requirements -> tests -> commits
evidence gaps     # NO COVERAGE / ORPHANED / UNTRACED / UNPROVEN, exit 0/1/2 -- see below
evidence export   # write the traceability matrix, --format csv|md, append-safe
```

A requirement counts as covered only when there is a genuine structural link — a test
declaration or explicit tag next to the requirement ID, or a `validation/traceability.csv`
row whose claim is independently corroborated against the file it names — never mere
proximity, and never an assertion nobody checked. `gaps` distinguishes three exit codes
that must never render the same: `0` (assessed, clean), `1` (assessed, gaps found), `2`
(nothing to assess — zero requirements found anywhere). `.evidence/adapter.yml` (see
`.evidence/adapter.example.yml`) tells it where a repository that doesn't use this
framework's own layout keeps its requirements, tests and tracker keys, so it can run
against repositories this framework never touched.

Full docs, a worked example against this repository's own real (and honestly imperfect)
traceability data, and the exit-code table: [`cli/README.md`](cli/README.md). Before
trusting its output on something that matters, read
[`cli/REVIEW-BRIEF.md`](cli/REVIEW-BRIEF.md) — a structural walkthrough and reviewer
checklist for the tool itself, written because it was built in one session with no
human reviewer and is the artifact most likely to reach someone outside the team.

## Risk tiering — ceremony scales with risk

Nine mandatory gates on every change recreates the process weight this framework exists
to remove.

```mermaid
flowchart TD
    CH(["A change"]) --> T3{"Touches audit trail, authn/authz,<br/>tenancy, key material, retention,<br/>regulated records, or a control<br/>a customer cites?"}
    T3 -- yes --> R3["TIER 3<br/>· full control tables, evidence impact<br/>· both review agents<br/>· two human reviewers<br/>· no auto-accept"]
    T3 -- no --> T2{"Production code path?<br/>new endpoint, integration,<br/>customer-visible behaviour"}
    T2 -- yes --> R2["TIER 2<br/>· intent + spec + plan<br/>· security agent<br/>· full diff read"]
    T2 -- no --> R1["TIER 1<br/>· plan only<br/>· automated checks<br/>· spot-check review"]

    R1 -. "in doubt?" .-> R2
    R2 -. "in doubt?" .-> R3

    style R3 fill:#fbe6e6,stroke:#c05050
    style R2 fill:#fdf0e3,stroke:#c98b3a
    style R1 fill:#e7f5ec,stroke:#4a9163
```

**When in doubt, tier up.** A Tier 2 change that was really Tier 3 is the failure that
matters.

## Rollout order

Each step is useful alone and makes the next cheaper. **Do not start with the gates** —
gating a process nobody follows yet just generates workarounds.

```mermaid
flowchart LR
    P0["PHASE 0<br/>Baselines +<br/>risk assessment<br/>(before install)"] --> P1["PHASE 1<br/>Discovery,<br/>ingest documents,<br/>CLAUDE.md,<br/>feedback loop"]
    P1 --> P2["PHASE 2<br/>Planning<br/>by default"]
    P2 --> P3["PHASE 3<br/>Open the front door<br/>(non-engineers)"]
    P3 --> P4["PHASE 4<br/>Encode the standards<br/>(as skills)"]
    P4 --> P5["PHASE 5<br/>Hooks behind the<br/>non-negotiables"]
    P5 --> P6["PHASE 6<br/>Review in<br/>both directions"]
    P6 --> P7["PHASE 7<br/>Close the loop"]

    style P0 fill:#fdf6e3,stroke:#b39b52
    style P5 fill:#fdf0e3,stroke:#c98b3a
    style P7 fill:#e7f5ec,stroke:#4a9163
```

**Phase 0 — before installing anything.** Capture the baselines in
`governance/baseline-metrics.md`. You cannot reconstruct them later, and without them
every impact claim is unfalsifiable. Start the tool risk assessment with your quality
function in parallel; it takes longer than the technical setup.

**Phase 1 — establish facts, then competence.** Run discovery, answer the `[ASK]`s,
commit `.evidence/context/`. Run `document-ingestion` on the procedures and requirement
documents that already govern your work — skipping this produces a parallel set of
markdown that drifts from your controlled documents, which is worse than not starting.
Then a one-page `CLAUDE.md` per repo, and a feedback loop: one command each for build,
test and lint, each exiting non-zero on failure. Run `legacy-characterization` in
parallel on the modules people are afraid of — it is the highest-value early use of an
agent, higher than feature work.

**Phase 2 — planning becomes the default.** Plan mode first, `plan.md` committed.

**Phase 3 — open the front door.** Non-engineering teams get `intent-capture`. Support
is the highest-leverage, lowest-cost group to onboard.

**Phase 4 — encode the standards.** One policy, one named owner, one source of truth.

**Phase 5 — hooks behind the non-negotiables.** Only now, and only after leadership,
change management and quality have listed the approvals that must survive.

**Phase 6 — review in both directions.** `REVIEW.md`, agent review passes, human
attention moved up a level to intent and risk.

**Phase 7 — close the loop.** Scheduled `evidence gaps` runs (see "The evidence CLI"
above) wired into CI so a coverage gap blocks a release the same way a failing test
does, control bands on production metrics, findings re-entering as `intent.md`.
Rehearse rollback before you get here.

## Measure these

Velocity and guardrails on the same page, always. Velocity gains that conceal a rising
failure rate are the classic failure of these programmes.

- Time from first conversation to committed `intent.md`
- Share of changes merging on the first implementation pass
- First-pass CI success rate for agent-written changes
- Defects caught before merge vs. escaping to production
- **Review depth** — review time per change, plus a quarterly spot-audit of whether
  approvals were substantiated. This is the only honest check on approval theatre
- **Evidence assembly time at release.** If the chain is working this collapses from a
  project to running `evidence export`. Usually the clearest number to show leadership

## On third-party plugins

The ecosystem is large and some of it makes this framework better — official security
tooling, document conversion, read-only documentation servers, browser automation for
test authoring. Some of it quietly disables the controls this framework exists to
provide: context compressors mean a security or compliance skill may never see the code
it was supposed to examine and will report a clean pass anyway; persistent cross-session
memory puts state outside version control; design "taste" plugins argue against an
established design system and win locally.

`docs/third-party-tooling.md` has the four questions to ask, the standing decisions, and
how something gets onto an allowlist.

Notably: **install Anthropic's `security-guidance` plugin and do not duplicate it.**
`secure-api-review` here deliberately covers only what a generic scanner cannot know.

## Adapting it

- **Fork it and make it yours.** These skills encode *someone's* standards. Replace the
  control checklists with your regulatory framework, replace the review policy with
  yours, delete the plugins you don't need.
- **Not in a regulated industry?** `evidence-sdlc`, `evidence-discovery` and
  `evidence-quality` stand alone. The artifact chain and traceability are worth having
  whether or not anyone audits you.
- **Different regulatory framework?** `regulatory-controls` is a worked example of the
  shape: a table of controls, each with a verdict and a pointer to evidence. Swap the
  rows for ISO 13485, SOC 2, IEC 62304, or whatever applies.
- Keep organisation-specific content in your fork, not in a public one.

## Caveats worth stating plainly

- **Human approval on a change nobody read is worse than no AI at all.** Risk-tier the
  work and measure review depth, or the control becomes a fiction.
- **If agents write most of the code, engineers do not build the judgement needed to
  review it.** That takes years to become visible and undermines the review-depth
  control directly — see [`governance/human-capability.md`](governance/human-capability.md).
  This is an open question the industry has not solved; writing it down is the point.
- **An agent inside your product is a different system** from an agent inside your
  development process. The risk assessment here covers the second, not the first.
- **Nothing here makes anything compliant.** These skills surface findings and evidence.
  Your quality function decides, and a human signs.

## Prior art

Shaped by Anthropic's AI-native SDLC playbook, AWS's AI-DLC methodology, and Andrej
Karpathy's LLM Council pattern. The synthesis, the discovery-first design and the
traceability model are this project's own.

## Licence

MIT — see [LICENSE](LICENSE).
