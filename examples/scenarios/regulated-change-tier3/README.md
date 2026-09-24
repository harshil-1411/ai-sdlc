# Scenario: a regulated change — electronic signature on a clinical document

**Who this is for:** a team whose product is subject to 21 CFR Part 11 (or an
equivalent electronic-records/electronic-signature regime), adding a genuinely
consequential capability: letting a reviewer electronically sign off on a document.
This is the heaviest, most complete path through the framework — read it after
[the non-regulated scenario](../new-feature-non-regulated/README.md) to see what
changes when the stakes are real.

## The story

> "As a QA reviewer, I want to electronically sign a batch record once I've reviewed
> it, so the signed state is legally attributable to me and cannot be altered
> afterward."

`.evidence/context/compliance.md` already records 21 CFR Part 11 as an applicable
framework, confirmed by a named quality owner, with "signed batch records" defined as
this product's regulated record type.

## Walkthrough

**1 · Plan.** `intent-capture` writes `intent.md` — **Regulated record impact: Yes.**
The signature itself is the regulated record. Compliance evidence impact: yes, this is
a new control a customer's own validation package will likely cite.

**Risk tier, stated immediately:** `risk-tiering` marks this **Tier 3** without
debate — it touches signature creation directly, which is on the Tier 3 list by
definition, not by judgement call.

**2 · Design.** `spec-and-design` produces a full `spec.md`:
- **Regulatory control table** — `regulatory-controls` loads
  `21-cfr-part-11.md` and checks each control (§11.50 signature manifestation:
  printed name, date/time with timezone, meaning of signing; §11.70 record linking:
  the signature is linked to the record so it can't be excised and reused
  elsewhere) with a verdict and a pointer to the design element that satisfies it.
- **Security design** — `secure-api-review` covers the new signing endpoint: who can
  invoke it, tenant isolation, and specifically that the signing key material never
  leaves the server boundary.
- **UX** — the states table includes what an already-signed record shows on a second
  view attempt (read-only, signature visibly displayed, no edit affordance at all).
- **Areas of concern** — this spec names one: whether re-opening a *rejected* review
  should count as "record integrity" or "record correction," routed to the named
  quality owner rather than decided silently.

**Decision point:** the choice between an HSM-backed signing key and an
application-managed one is a one-way door (expensive to reverse, touches key
material). The team runs `decision-council`'s **Lite** variant (four passes, one
session) — full council would be reserved for something even more consequential, per
that skill's own guidance not to let it become a ritual.

The spec states the comparison's evidence explicitly, not just its conclusion:
- **Evidence tier and support.** "HSM-backed keys keep signing material
  non-exportable" rests on **Tier 2** (the HSM vendor's FIPS 140-2 conformance
  spec) — **supported**, not asserted. "Application-managed keys are adequate if
  encrypted at rest" rests on **Tier 4** (an unattributed industry best-practice
  claim someone remembered from a prior job) — **weakly supported**: nobody could
  point to a source for it when asked directly, which is exactly why this
  decision escalated to decision-council instead of being picked silently.
- **Reversibility line, named across its four factors:** reversibility — low,
  once signed records exist under one key model, migrating them to the other
  means re-signing or accepting a mixed-model audit trail, either of which is its
  own Tier 3 change; coupling — the signing interface is designed key-model-
  agnostic specifically to keep this factor from being worse than it has to be;
  portability — HSM vendor lock-in is real (proprietary key-ceremony tooling),
  application-managed has none; switching cost — re-provisioning and
  re-attesting every signer is a multi-week operational exercise either
  direction, not a config change.
- **Review trigger:** revisit this decision if transaction volume grows enough to
  require a second region and the HSM vendor's per-region licensing changes the
  cost comparison materially, or if the vendor's FIPS conformance certification
  lapses before renewal — either event reopens a decision that was otherwise
  closed, rather than leaving it to be rediscovered by accident during an
  unrelated audit.

**3 · Build.** Per Tier 3's Definition of Ready, `codebase-grounded-planning`'s plan
gets sign-off from **both** a named technical lead and the product owner. One of them
records the approval against the plan's hash (`/evidence-sdlc:approve <KEY> <sha>`).
The change was started with `--tier 3`, and it has to be: `**/signing/**` and
`**/migrations/**` carry Tier 3 floors in policy. The plan touches `migrations/` (a
new `signature` table), which is under change control, so the human who starts the
session must also set `CHANGE_TICKET` to the approved change record before the engine
allows that edit. Tier 3 also means no auto-accept permission modes.

**4 · Test.** `test-strategy` requires, per requirement: the signature is
cryptographically verifiable, the audit trail records who/when/what-was-signed, and a
tampered record's signature fails verification. Automated where possible; the
tamper-detection case is deliberately adversarial, not just a happy-path check.

**5 · Deploy.** Tier 3's Definition of Ready requires **two human reviewers**: the
code owner reads the full diff, and a second reviewer independently examines the
regulated portion specifically. `compliance-reviewer` (agent) runs a controls +
validation pass over the diff before the PR opens. The engine won't allow a push or
`gh pr create` until `verifier`, `security-reviewer` and `code-reviewer` have recorded
runs. See [v2-gates-in-action](../v2-gates-in-action/README.md) for what those
denials look like.

**6 · Maintain.** The release record includes a **validation impact assessment**, not
just "no impact" — a customer relying on this control in their own validation package
needs to know it changed. `evidence-package` derives this from the artifact chain
rather than someone writing it from memory at release time.

## What made this Tier 3, concretely

Not "it's in a regulated product" generally — risk-tiering is specific: *touches
signature creation*. A change to this same product's marketing site would be Tier 1.
The tier follows the change, not the whole codebase.

## Read next

- [`risk-tiering`](../../../plugins/evidence-sdlc/skills/risk-tiering/SKILL.md)
- [`regulatory-controls`](../../../plugins/evidence-compliance/skills/regulatory-controls/SKILL.md)
  and its [21 CFR Part 11 reference](../../../plugins/evidence-compliance/skills/regulatory-controls/references/21-cfr-part-11.md)
- [`decision-council`](../../skills/decision-council/SKILL.md) (optional skill, kept
  in `examples/` — see its own README for why)
- [Scenario: a regulated-table schema migration](../schema-migration-regulated-table/README.md) —
  what happens when this same signed-record table needs to change shape later
- [Scenario: proving a regulated-record case, not just naming it](../qa-evidence-profile/README.md) —
  the evidence profile and case design made concrete for a later change to this
  same signed-record table
