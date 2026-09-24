---
name: risk-tiering
description: Classify a change into risk tier 1, 2 or 3, record it, and apply the matching Definition of Ready, review depth and Definition of Done so ceremony lands where the risk is. Use at the start of every intent, spec and plan, when someone asks "what tier is this", "how much process does this need", "what review does this need", or checks a Definition of Ready or Done, and before proposing any gate.
---

# Risk tiering

Process weight lands where the risk is. Routine work is not buried in ceremony;
regulated work does not skip it.

## Tiers

**Tier 3 — Regulated / high risk.** Touches: the audit trail, signature creation or
verification, record integrity or retention, authentication, authorisation, tenant
isolation, key material, data residency, or any behaviour a customer's validation
package asserts. Also: any schema migration on a regulated table, and any change to
this framework's own gates.

**Tier 2 — Elevated.** Touches a production code path that is not regulated: new
endpoints, new external integrations, performance-sensitive paths, anything customer-
visible in a way that generates support load.

**Tier 1 — Routine.** Internal tooling, non-regulated UI polish, documentation,
dependency patch within an approved range, test additions, refactors fully covered by
existing tests.

**Technical debt raises the tier; it never lowers it.** Before settling on a tier from
the definitions above, check whether the area being touched already carries
accumulated debt: a documented workaround, a prior incident referenced in git history
or a known-issues doc (if one exists), or test coverage that is thin relative to the
rest of the codebase. If any of those signals is present, raise the effective tier by
one notch — Tier 1 becomes Tier 2, Tier 2 becomes Tier 3. As with the override rule
below, this may never weaken a tier's ceiling in the other direction: debt can only
push a change up, never down, and never past Tier 3.

**Policy tier floors are a minimum, not a suggestion.** The repository policy maps
paths to a minimum tier (for example `**/auth/**` and `**/migrations/**`). Check the
paths the change will touch against those floors before choosing. An edit to a path
whose floor is above the change's recorded tier is denied.

**When in doubt, tier up.** A Tier 2 change that was really Tier 3 is the failure mode
that matters.

## Record the tier

State the tier as `Risk tier: <n> — <reason>` (n is 1, 2 or 3). This one notation is
used everywhere: the first line of your response when you classify, and a header line in
`spec.md` and `plan.md`. Then record it in the change's state:

`evidence change start <KEY> --tier <n> --kind feature|fix|chore`

`.evidence/changes/<KEY>/state.json` is the record the gates read; the `Risk tier:`
lines must agree with it. If the tier later needs raising — new paths hit a policy floor,
or the work turned out riskier — say so and ask a human to run
`evidence change set-tier <KEY> <n>`. Never lower a recorded tier yourself, and never
work around a floor denial by moving the edit to an unfloored path.

**An override may narrow scope or supply a missing credential; it may never weaken a
tier's ceiling.** The gates accept a few human-supplied values — `CHANGE_TICKET`,
`RELEASE_APPROVAL`, `EVIDENCE_ACTIVE_CHANGE`, `EVIDENCE_SOURCE_GLOB` among them. Each is
legitimate because it supplies the specific thing a gate checks for (an accountability
record, an authorisation, which change is active) or narrows which paths are in scope.
None of them may make a change run at a lower tier's ceremony than its risk requires.
`CHANGE_TICKET` lets a change-controlled edit proceed because the accountability record
now exists; it does not exempt the change from needing one. The agent never supplies
these values itself. Hold every new gate or override to this rule: it can make a
requirement satisfiable, never optional.

## What each tier requires

The artifact rows match what `evidence change status` checks: Tier 1 needs a plan,
Tier 2 a spec and a plan, Tier 3 an intent, a spec and a plan.

| | Tier 1 | Tier 2 | Tier 3 |
| --- | --- | --- | --- |
| `intent.md` | Optional (ticket suffices) | Optional (ticket suffices) | Required |
| `spec.md` | Not required | Required | Required + areas of concern routed to named owners |
| `plan.md` | Required (all tiers — the engine enforces it) | Required | Required, plus rejected alternatives |
| Plan approval | Human, via `/evidence-sdlc:approve` | Human, via `/evidence-sdlc:approve` | Human, via `/evidence-sdlc:approve` |
| regulatory control table | No | Only if regulated-adjacent | Full table, every control given a verdict |
| Validation impact assessment | No | Statement of "no impact" with reason | Full, with revalidation call |
| Security review pass | Automated only | Automated + `security-reviewer` agent | Both + named Security owner sign-off |
| Compliance review pass | No | No | `compliance-reviewer` agent + sign-off by the roles `compliance.md` names |
| Review agent runs recorded (before `verified`; push checks them at Tier 2+) | `verifier` | `verifier`, `security-reviewer` | `verifier`, `security-reviewer`, `code-reviewer` |
| Human review depth | Code owner reviews the summary and spot-checks | Code owner reads the full diff | Code owner reads the full diff **and** a second reviewer independently examines the regulated portion |
| ADR in `.evidence/decisions/` | No | For one-way doors | For any architecture or data-model choice |
| Auto-accept mode | Permitted | Permitted with tests covering the path | Not permitted — the engine denies edits under auto-accept modes |

## Definition of Ready (tiered)

Tier 1: problem stated, acceptance stated, plan on disk.
Tier 2: the above, plus API/data impact understood and test scenarios identified.
Tier 3: the above, plus regulatory control impact assessed for each framework in
`.evidence/context/compliance.md`, validation impact assessed, security impact assessed,
rollback plan named, and the sign-off roles compliance.md names made aware. If
compliance.md is missing, that is an `[ASK]`, not an assumption.

## Definition of Done (tiered)

Tier 1: merged, tests pass, lint clean.
Tier 2: the above, plus security pass clean, docs updated, release note entry.
Tier 3: the above, plus compliance pass clean, traceability rows updated, validation
impact recorded, an ADR in `.evidence/decisions/` for each lasting design decision, and
the sign-offs compliance.md requires attached.

## State the tier before any design work

No schema, data model, API contract or architecture is produced without a stated
tier. If asked to design something directly, state the tier first, in one line,
with the reason. A design for a regulated record is Tier 3 by definition.

This still applies when something else blocks you from producing the design
itself — most commonly `spec-and-design`'s or `codebase-grounded-planning`'s
stop-if-no-stack-profile precondition. The tier statement must be the literal
first line of your entire response — before a heading, before "Stopped at...",
before acknowledging the stop, before anything else — using what you already
know from the request (the entity involved, whether it looks regulated, who is
affected). Write it in exactly this form, as its own line, nothing above it:

`Risk tier: <1|2|3> — <one-line reason>.`

Only after that line do you explain a stop, ask clarifying questions, or write
anything else. Do not fold the tier into a bullet list, do not bury it under a
"What I need from you" or numbered-questions section, and do not leave it as
an open question ("this decides whether it's Tier 2 or 3") — commit to a tier
now on the information available, and say plainly if a fact you're missing
could raise it later. A stopped response that states the tier anywhere other
than as its first line is treated the same as not stating it at all — a
correct-but-buried tier is still an incomplete application of this skill.

## Review-depth honesty

Human approval on a change nobody read is worse than no AI at all — it converts a
control into a fiction, and that is what an inspector will probe. If you are asked to
approve a Tier 3 change and have not read the regulated portion of the diff, say so
rather than approving. That refusal is the control working.

Plan approval is never the agent's to give. Ask the human to run `/evidence-sdlc:approve <KEY> <plan-sha>`
(or `evidence approve <KEY>` in their own terminal); never write an approval file or an
"Approved by" line yourself.
