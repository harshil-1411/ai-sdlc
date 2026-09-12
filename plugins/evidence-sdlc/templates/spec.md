# Spec: <short title>
Tracker: <KEY>   From: intent/<...>/intent.md   Risk tier: 1 | 2 | 3

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
<Apply the `architecture-diagrams` skill. Include only the diagrams this change needs;
delete the headings you do not use. Diagrams live in the repo as code, not as links.>

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

## Rejected alternatives
<What was considered and why it lost. Link the ADR if a council was convened.>
