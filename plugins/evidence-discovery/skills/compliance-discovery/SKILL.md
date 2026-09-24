---
name: compliance-discovery
description: Establish which regulations, standards and contractual obligations actually apply to a project and write them to .evidence/context/compliance.md. Use at onboarding, when a new market or customer segment is entered, and on plain questions like "are we HIPAA/SOC2/GDPR/PCI compliant", "is this regulated", "what regulations apply to us" — even when a README seems to answer it. Never assume a framework applies, and never assume none does.
---

# Compliance discovery

**No skill in this framework assumes a regulatory framework.** A tool that hardcodes one
regulation is useless to everyone outside that industry and, worse, gives everyone
inside a neighbouring one false confidence that they are covered.

This runs once per project alongside stack discovery, and everything downstream reads
its output.

## Do not offer — run

Do not ask "would you like me to run compliance discovery?". If someone asks what
regulations apply, a new market or customer segment is entered, or a spec could touch
a regulated record, and no profile exists, run Step 1's evidence gathering and put
Step 2's questions to the accountable human directly — do not ask permission first to
go gather that evidence and ask those questions.

## Rule — this is a question for humans, not an inference

Discovery of a *stack* can be done from files. Discovery of *applicable regulation*
cannot. A repository does not tell you which markets your product is sold into, which
contractual commitments exist, or what your customers assert in their own audits.

So: gather evidence where it exists, then **ask**, and record who answered. An answer
sourced from a person with a name and a date is the only acceptable outcome here. Do not
infer a framework from the presence of a word in a README.

## Step 1 — gather what evidence exists

Before asking, look for signals so the questions are informed rather than blank:
- Existing policy, quality-manual or SOP documents in the repository or wiki
- Certification badges, audit reports, trust-centre pages
- Contractual language in customer-facing documents
- Existing controls in code: audit trails, retention logic, consent handling, residency
  configuration, encryption boundaries, access-review tooling
- Data classes the system stores — health data, payment data, personal data of specific
  jurisdictions, government data
- Any existing validation, qualification, or certification artifacts

Present what you found as context for the questions, not as an answer.

## Ask only for what is essential and missing

Ask only for information that is (a) genuinely absent from the repository and
(b) would change what you produce. If an answer would not change the output,
do not ask for it.

Batch questions into one round where possible rather than interrogating turn by
turn. Order them most-consequential first. A question you could have answered by
reading a file is a question you should not have asked.

## Step 2 — the questions

Put these to the accountable person — typically a quality, compliance, legal or security
owner, not an engineer:

1. **What industry and market segments does this product serve?** Life sciences,
   healthcare delivery, financial services, payments, government, education, general
   commercial.
2. **Which jurisdictions?** Where are customers, where is data stored, where is it
   processed.
3. **Which frameworks apply, and in what role?** For each: is it a legal obligation, a
   contractual commitment, a certification we hold, or a standard we claim alignment
   with but are not audited against? These are very different obligations and are
   routinely conflated.
4. **Do customers rely on our controls in their own audits or validation?** If yes, our
   changes have consequences inside their compliance posture, which raises the risk tier
   of anything touching a control they cite.
5. **What are our regulated record types?** Define them concretely for this product. This
   single definition is used by every other skill in this framework, so it has to be
   specific enough that an engineer can decide, unaided, whether a change touches one.
6. **Who is the named owner of each framework?** Findings route to a person.
7. **What audits or inspections do we undergo, by whom, and when next?**
8. **What is explicitly out of scope?** Recording what does *not* apply is as valuable as
   recording what does, and it stops a well-meaning session applying a control set that
   costs money and buys nothing.

## Step 3 — write the profile

Write `.evidence/context/compliance.md` from the template. For each framework, record
the identifier of the control-set reference the `regulatory-controls` skill should load
from `references/`, or note that a custom control set must be authored.

Mark every entry `[confirmed]`, `[inferred]` or `[ASK]` like the other profiles. A
framework marked `[inferred]` must not be treated as authoritative — it is a prompt to
get a real answer.

## Step 4 — the "none apply" case is a real answer

Plenty of products carry no regulatory obligation beyond general data protection. Record
that explicitly, with who confirmed it, and the artifact chain, traceability and testing
parts of this framework still stand on their own. Silence is not the same as "none
apply"; an empty profile means nobody has asked.

## When to re-run

- Entering a new market or jurisdiction
- A new customer segment with different obligations
- Storing a new class of sensitive data
- A framework being revised
- Annually, regardless

## Output feeds

- `regulatory-controls` — loads the matching control set and applies it during design and review
- `evidence-package` — knows which deliverables the frameworks require
- `risk-tiering` — knows which paths are regulated and therefore Tier 3
- `intent-capture` and `spec-and-design` — ask the right impact questions
