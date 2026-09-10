---
name: risk-tiering
description: Classify a change into a risk tier and apply the matching Definition of Ready, review depth, and Definition of Done, so process weight lands where the risk is. Use this at the start of every intent, spec and plan, whenever someone asks how much process a change needs, whenever a Definition of Ready or Done is being checked, and whenever review is being assigned. Apply it before proposing any gate, so routine work is not buried in ceremony.
---

# Risk tiering

Nine mandatory gates on every change is the process weight we are trying to remove.
The point of AI-native SDLC is not more gates — it is gates that land where the risk is.

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

**When in doubt, tier up.** A Tier 2 change that was really Tier 3 is the failure mode
that matters. Say which tier you chose and why, in one line, in the spec.

## What each tier requires

| | Tier 1 | Tier 2 | Tier 3 |
| --- | --- | --- | --- |
| `intent.md` | Optional (ticket suffices) | Required | Required |
| `spec.md` | Not required | Required | Required + areas of concern routed to named owners |
| `plan.md` | Required (all tiers — the hook enforces it) | Required | Required, plus rejected alternatives |
| regulatory control table | No | Only if regulated-adjacent | Full table, every control given a verdict |
| Validation impact assessment | No | Statement of "no impact" with reason | Full, with revalidation call |
| Security review pass | Automated only | Automated + `security-reviewer` agent | Both + named Security owner sign-off |
| Compliance review pass | No | No | `compliance-reviewer` agent + QA/RA sign-off |
| Human review depth | Code owner reviews the summary and spot-checks | Code owner reads the full diff | Code owner reads the full diff **and** a second reviewer independently examines the regulated portion |
| Decision council | No | Only for one-way doors | For any architecture or data-model choice |
| Auto-accept mode | Permitted | Permitted with tests covering the path | Not permitted — per-change review |

## Definition of Ready (tiered)

Tier 1: problem stated, acceptance stated, plan on disk.
Tier 2: the above, plus API/data impact understood and test scenarios identified.
Tier 3: the above, plus Part 11 impact assessed, validation impact assessed, security
impact assessed, rollback plan named, and QA/RA aware.

## Definition of Done (tiered)

Tier 1: merged, tests pass, lint clean.
Tier 2: the above, plus security pass clean, docs updated, release note entry.
Tier 3: the above, plus compliance pass clean, traceability rows updated, validation
impact recorded, ADR stored if a design decision was made, QA/RA sign-off attached.

## Review-depth honesty

Human approval on a change nobody read is worse than no AI at all — it converts a
control into a fiction, and that is what an inspector will probe. If you are asked to
approve a Tier 3 change and have not read the regulated portion of the diff, say so
rather than approving. That refusal is the control working.
