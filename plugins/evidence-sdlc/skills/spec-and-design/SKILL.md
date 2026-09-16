---
name: spec-and-design
description: Produce a reviewable requirements-and-design spec.md from an accepted intent.md, with the organisation security, compliance, UX and API standards applied while the spec is written and every conflict flagged. Use this whenever an intent has been accepted, whenever someone asks for a design, a solution approach, an API design, or a technical approach document, and before any implementation planning begins. Also trigger on direct design requests that use no process vocabulary at all — "design the schema", "design the data model", "design the API", "how should we structure...", "what should the table look like", "model this", "what fields do we need", "sketch the design" — those are still design work and still need a spec, not just an answer. Do not let work jump from intent straight to code.
---

# Requirements and design (Stage 2: Design)

## Precondition — stop if there is no stack profile

Read `.evidence/context/stack.md` before anything else. If it does not exist,
STOP. Do not produce a spec, a design, a schema, or a plan. Say that discovery
has not run and that designing against unverified stack facts is how confidently
wrong designs get built. Run stack-discovery, then resume.
This is not a warning to note and move past. It is a stop.

If the profile exists but carries an unresolved [ASK] in an area this change
depends on, that is also a stop — ask the human.

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

## Mark what you have not verified

Any factual claim you did not confirm from a file you read, a command you ran, or
a person who told you, is marked inline as [NEEDS VERIFICATION]. This includes:
performance characteristics, third-party API behaviour, capacity and cost figures,
claims about how an existing system behaves, and anything sourced from
documentation rather than code.

An unmarked claim asserts that you checked it. Do not make that assertion loosely.
A reviewer should be able to find every unchecked claim by searching the file.

### For a consequential claim, name the evidence tier too

A [NEEDS VERIFICATION] tag says a claim is unchecked; it does not say how strong
the evidence behind it actually is, or would be. For anything of real consequence
— a security, compliance, cost, or resilience claim, not a cosmetic detail — name
which tier backs it:

| Tier | Backed by |
| --- | --- |
| 1 | A regulation, an internal policy, or this system's own telemetry |
| 2 | Vendor documentation or a published benchmark |
| 3 | A reference architecture |
| 4 | A general best practice, unattributed |
| 5 | Inference alone — no external source |

Pair the tier with a support classification: **supported** (the tier-appropriate
source directly confirms the claim), **conditionally supported** (confirms it under
a stated assumption), **weakly supported** (the source is suggestive, not
conclusive), **unverified** (no source checked yet), or **contradicted** (a source
says otherwise, and this claim needs to change or the source needs to be argued
against explicitly, not ignored).

A consequential claim rated Tier 4 or 5, or classified weakly supported or
contradicted, is not a detail to tag and move past — route it to **Areas of
concern** with a named owner, the same as any other unresolved conflict.

## Rules

- Where a standard exists, cite it rather than restating your own version.
- If the change is high-risk (touches signing, audit trail, authentication,
  tenant isolation, key material, or a validated workflow), say so in a
  `Risk classification:` line at the top. High-risk specs need a named technical
  lead as well as the product owner before they progress.
- If the decision between two designs is genuinely close and expensive to reverse,
  stop and say so rather than picking silently. `decision-council` (optional, not
  installed by default — see `examples/skills/decision-council/`) is the
  multi-perspective pressure test for exactly this; install it, or at minimum do
  the following before deciding:
  - **Name at least two genuinely different approaches** — not a strawman and the
    real one. Reuse what `codebase-cartographer` already found; do not re-explore
    to produce these. For each, state what it touches, which existing pattern it
    fits or breaks, and its cost to reverse later.
  - **State a recommendation with reasoning** — which approach and why, not just
    a list of options with no opinion.
  - **State the reversibility line explicitly, and name what it actually depends
    on** — is this a one-way door, and why: how reversible is it, how tightly
    coupled does it make things that were previously separate, how portable does
    the result stay if you need to move away from it later, and what would it
    cost to switch away. Naming these four is what makes "reversibility" a
    judgement a reviewer can check, not a word.
  - **State a review trigger** — a named condition under which this decision
    should be revisited, not treated as settled forever: a traffic threshold, a
    vendor pricing or deprecation event, a compliance-scope change. A decision
    with no review trigger reads as permanent even when it was only ever the
    right call under today's constraints.
  - **Write the comparison into `spec.md`'s "Rejected alternatives" section** —
    the rejected approach and the reasoning that decided against it, not a
    one-line "considered and lost," and the review trigger alongside it. This is
    the record a later reviewer or an inspector reads; the reasoning has to
    survive without you in the room.

  This only fires under the condition already named above — genuinely close and
  expensive to reverse. It is not a new step for every Tier 2+ spec, and does not
  lower the bar for when `decision-council` itself should be convened instead.

## Done means

`spec.md` is committed next to `intent.md`, every requirement has an ID, and the
areas of concern are routed to named owners.
