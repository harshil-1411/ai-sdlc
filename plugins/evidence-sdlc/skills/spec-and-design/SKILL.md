---
name: spec-and-design
description: Produce a reviewable requirements-and-design spec.md from an accepted intent.md, with the organisation security, compliance, UX and API standards applied while the spec is written and every conflict flagged. Use this whenever an intent has been accepted, whenever someone asks for a design, a solution approach, an API design, or a technical approach document, and before any implementation planning begins. Do not let work jump from intent straight to code.
---

# Requirements and design (Stage 2: Design)

You are collapsing "analyst writes requirements" and "designer writes design" into
one session. The product owner reviews the output; they do not write it.

## Inputs you must have

- The accepted `intent.md` (read it in full, do not summarize from memory).
- The repository profile: `.evidence/context/stack.md`, `deployment.md`, `toolchain.md`
  and `design-system.md`. Never assert a technology, deployment target or component
  that is not in the profile or in a file you read. An unresolved `[ASK]` in a relevant
  area blocks the spec — ask, do not assume.
- The current codebase. Use the `codebase-cartographer` agent to find what already
  exists before proposing anything new. Duplicated core-domain logic is a recurring and
  expensive mistake in long-lived products.
- The tracker issue key. Apply the `traceability-ids` skill; the spec header carries it.

## What the spec must contain

Use `${CLAUDE_PLUGIN_ROOT}/templates/spec.md`. Non-negotiable sections:

- **Requirements**, each with a stable ID (`REQ-<area>-<nn>`) and each traceable
  back to a line in `intent.md`. These IDs are what the validation package cites.
- **Regulatory control impact**: one table per framework listed in
  `.evidence/context/compliance.md`. Apply the `regulatory-controls` skill and quote its
  findings. If no framework applies, say so with the reason — that sentence is evidence.
- **Evidence impact**: which existing requirement entries or evidence deliverables
  change? Apply the `evidence-package` skill.
- **Security design**: threat notes for any new endpoint, new trust boundary, new
  storage location, or new third-party call. Apply `secure-api-review`.
- **Data classification and residency**: Products with regional deployments; say
  which regions this changes and whether data crosses one.
- **UX**: the states, the empty/error/loading behaviour, and the accessibility
  requirement. Do not hand-wave "standard form".
- **Areas of concern**: an explicit list. Every place where two of our policies
  pull in opposite directions, or where you could not satisfy a standard, goes
  here with the policy owner named. This section being empty is suspicious — say
  so if it is.

## Integrations

If the change calls, or is called by, anything outside the platform, apply the
`integration-change` skill and give it its own spec section. An integration is a trust,
availability and compliance boundary at once.

## Rules

- Where a standard exists, cite it rather than restating your own version.
- If the change is high-risk (touches signing, audit trail, authentication,
  tenant isolation, key material, or a validated workflow), say so in a
  `Risk classification:` line at the top. High-risk specs need a named technical
  lead as well as the product owner before they progress.
- If the decision between two designs is genuinely close and expensive to reverse,
  stop and run the `decision-council` skill instead of picking silently.

## Done means

`spec.md` is committed next to `intent.md`, every requirement has an ID, and the
areas of concern are routed to named owners.
