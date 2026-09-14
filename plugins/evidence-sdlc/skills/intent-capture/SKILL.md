---
name: intent-capture
description: Turn a raw idea, ticket, customer escalation or production anomaly into a committed intent.md using the organisation's template. Use this whenever anyone — product, support, UX, QA, sales engineering, or an on-call engineer — starts describing something they want built, changed, or fixed, even if they never say the word "intent", "requirement" or "story". If someone is about to describe work in prose, capture it here first.
---

# Capture intent (Stage 1: Plan)

Nothing enters the SDLC except as an `intent.md`. This is the front door
for every team, not just engineering.

## What you do

1. Let the originator describe the problem in their own words. Do not make them
   use ticket language.
2. Interview them like a business analyst would. You must have answers, or an
   explicit "unknown", for all of:
   - What can't they do today, and who is affected (internal role, or a customer persona)?
   - Is a **regulated record** involved? Anything a customer would cite in an audit or
     inspection — signed or approved records, audit trails, consent records — is regulated.
     Define the term for your product once, in `CLAUDE.md`, and apply it consistently.
   - Does this change anything **our compliance evidence, or a customer's own
     validation, asserts** — a stated requirement, a tested workflow, a documented
     control? If yes, say so loudly: it is a re-verification impact, not just a code
     change. Read `.evidence/context/compliance.md` for what applies.
   - What does "better" look like, in a form someone could measure?
   - What is explicitly out of scope?
3. Ask about data classification: which classes of sensitive data does this touch?
   Use the classes your organisation already defines; do not invent new ones.
4. Write the result to `intent/<yyyy-mm-dd>-<slug>/intent.md` using the template at
   `${CLAUDE_PLUGIN_ROOT}/templates/intent.md`. Fill every heading; write "Unknown —
   needs <role>" rather than deleting a heading.
5. Show it to the originator, correct what you misunderstood, and commit it.

## Ask only for what is essential and missing

Ask only for information that is (a) genuinely absent from the repository and
(b) would change what you produce. If an answer would not change the output,
do not ask for it.

Batch questions into one round where possible rather than interrogating turn by
turn. Order them most-consequential first. A question you could have answered by
reading a file is a question you should not have asked.

**"Whatever you think" is not an answer.** If the originator declines to answer a
genuinely essential question — "whatever you think," "you decide," "I don't know,
you pick" — do not let that become an unstated assumption. Write your own best
guess into the intent.md draft explicitly, in the open, and get their confirmation
on that specific guess before treating it as settled. A shrug is not the same as
a decision.

## Rules

- **Do not design.** No API shapes, no table names, no component names. If the
  originator proposes a solution, record it under "Proposed outcome" as *their*
  proposal and keep the problem statement separate.
- **Do not estimate.** Sizing happens after the spec.
- If the person is describing an incident rather than a feature, still write an
  `intent.md`: put the anomaly and its evidence under Problem.
- Flag, do not resolve, anything that looks like it needs Legal, QA/RA, or Security.
  Name the function that must decide.

## Done means

`intent.md` is committed, the author and timestamp are in git history, and the
product owner can accept or reject it without another meeting.
