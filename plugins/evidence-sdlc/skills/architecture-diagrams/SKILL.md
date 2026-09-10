---
name: architecture-diagrams
description: Produce architecture, sequence, state and data-flow diagrams as version-controlled code that lives alongside the spec it describes. Use this whenever a spec or design needs a diagram, whenever someone asks for an architecture picture, whenever a system or integration is being explained, and whenever an existing diagram no longer matches the code. Never link to an image or an external design tool as the canonical diagram.
---

# Diagrams as code

A diagram in a design tool is a screenshot with a URL. A diagram as code is an artifact:
it lives next to the spec, it is reviewed in the diff, it changes in the same commit as
the thing it describes, and it appears in the audit trail like everything else.

That is the whole argument. It is the same argument as the rest of this framework.

## Choose the form by what you need

**Text-based diagram markup** (Mermaid and similar) for anything that renders inline in
a pull request or a documentation site: sequence diagrams, state machines, entity
relationships, simple component graphs, decision flows. This is the default — it needs
no build step, it diffs readably, and reviewers see it without leaving the PR.

**Code-rendered diagrams** (a diagram-generation library invoked from a script) for
infrastructure and deployment topology, where vendor iconography carries real meaning
and the diagram is large enough that markup becomes unreadable. These need a render step
in the pipeline; commit both the source and the rendered output so the PR shows the
picture and the diff shows the change.

## Which diagrams a spec actually needs

Do not draw everything. Each diagram must answer a question a reader will otherwise ask:

| Diagram | Include when |
| --- | --- |
| Component / context | The change adds or moves a service, or crosses a system boundary |
| Sequence | Ordering matters — approvals, retries, async flows, anything where "then what" is non-obvious |
| State machine | A record moves through states with rules about legal transitions |
| Data flow | Sensitive data moves, crosses a trust boundary, or leaves a residency zone |
| Deployment topology | Infrastructure changes |

For regulated work, the **data flow diagram is the one that earns its place**. It is what
lets a reviewer see, without reading code, where a regulated record travels, where it is
persisted, where it crosses a boundary, and where the audit trail records that crossing.

## Rules

- **The diagram lives in the repository**, next to the spec, in a `diagrams/` directory
  or inline in the markdown. Never a link to an external tool as the canonical version.
- **Update it in the same commit as the change.** A diagram that no longer matches the
  code is worse than none — people trust it and are misled. Treat a stale diagram found
  in review as a finding.
- **Label trust boundaries explicitly** on any diagram touching security or regulated
  data. An unmarked boundary is the thing everyone assumes someone else checked.
- **No credentials, no internal hostnames, no account identifiers** in a diagram that
  might be exported to a customer or an auditor.
- **Generate from reality where you can.** A diagram derived from infrastructure code or
  from the actual dependency graph will not drift. A hand-drawn one will.

## For the spec

`spec.md` has a Diagrams section. Fill it with the diagrams the table above says the
change needs, and delete the rest of the section rather than leaving empty headings.
