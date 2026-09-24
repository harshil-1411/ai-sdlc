# Spec: <short title>
Tracker: <KEY>   From: intent/<...>/intent.md
Risk tier: <1|2|3> — <one-line reason; name any policy tier floor that applies>

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Requirements
| ID | Requirement | Source (intent.md section) | Acceptance |
| --- | --- | --- | --- |
| REQ-<area>-01 | | | |

## Design
<Modules touched, data flow, API contracts, state. Reference what already exists —
list the existing components the cartographer found and say why each is extended or not.>

## Regulatory control impact
<Apply the `regulatory-controls` skill. Load the control sets named in
.evidence/context/compliance.md. One table per applicable framework. Every control gets
a verdict; "N/A" is allowed, silence is not.>

| Framework | Control ID | Applies? | How it is satisfied | Evidence |
| --- | --- | --- | --- | --- |

## Evidence impact
<Apply the `evidence-package` skill. Which requirement entries are added, modified or
retired; re-verification call and justification. "Out of regulatory scope because X" is
a valid and useful answer.>

## Diagrams
<Diagrams as code: the diagram lives in the repository, next to this spec, in a
diagrams/ directory or inline in this file — never a link to an external design tool
as the canonical version. Prefer text-based markup (Mermaid and similar) by default;
it needs no build step, diffs readably, and reviewers see it without leaving the PR.
Reserve a code-rendered diagram (a generation script with a committed render step)
for infrastructure/deployment topology where vendor iconography carries real meaning.
Update the diagram in the same commit as the change it describes — a diagram that no
longer matches the code is worse than none. Label trust boundaries explicitly on any
diagram touching security or regulated data. No credentials, internal hostnames, or
account identifiers in a diagram that might reach a customer or an auditor.

Include only the diagrams this specific change needs; delete the headings below you
do not use, per the table:

| Diagram | Include when |
| --- | --- |
| Component / context | The change adds or moves a service, or crosses a system boundary |
| Sequence | Ordering matters — approvals, retries, async flows |
| State machine | A record moves through states with rules about legal transitions |
| Data flow | Sensitive data moves, crosses a trust boundary, or leaves a residency zone — for regulated work this is the diagram that earns its place |
| Deployment topology | Infrastructure changes |
>

- Component / context:
- Sequence:
- State machine:
- Data flow (required if regulated data or a trust boundary is involved):
- Deployment topology:

## Security design
<New trust boundaries, new endpoints and their authorization, tenancy scoping,
new egress, new dependencies. Findings from secure-api-review.>

## UX
<Delete rows that do not apply; do not delete the table.>

| State / concern | Behaviour |
| --- | --- |
| Loading | |
| Empty | |
| Error | |
| Success | |
| Partial / stale data | |
| Edge cases (long values, zero, maximum, unusual input) | |
| Responsive behaviour | |
| Keyboard navigation | |
| Screen reader / assistive technology | |
| Focus management | |

Component reuse: <which existing components from design-system.md this uses, and
justification for anything new>

## Areas of concern
<Every conflict between standards, every unsatisfiable constraint, each with the
named policy owner who must decide. Do not leave this empty by default.>

## Architecture decisions
<Every decision with lasting consequence has an ADR at `.evidence/decisions/NNNN-<slug>.md`
(template: `templates/adr.md`, drafted by the `architect` agent). List each ADR this spec
creates, supersedes or relies on, and any conflict with an existing one. "None — no
decision here outlives this change" is a valid answer.>

| ADR | Created / Supersedes / Relies on | Status |
| --- | --- | --- |

## Rejected alternatives
<What was considered and why it lost. Link the ADR that records it. For a genuinely
close decision, name the review trigger — the condition under which this should be
revisited.>
