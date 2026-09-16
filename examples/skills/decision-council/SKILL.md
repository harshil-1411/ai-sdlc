---
name: decision-council
description: Pressure-test a consequential and hard-to-reverse decision by running it past several independent expert perspectives that then critique each other, before a chair synthesizes a recommendation. Use this when someone says "council this", "pressure-test this", "stress-test this", "war room this", or when a design choice is close, expensive to reverse, or touches a validated workflow — and use it proactively when a spec or plan is about to lock in an architecture, a data model, a vendor, or a migration path.
---

# Decision council

Adapted from the LLM Council pattern (Karpathy), tuned for regulated product work. The purpose is to surface the objection nobody in the room was paid to
raise — before it becomes a spec.

## When to convene

Convene for: architecture that is hard to reverse, data model or migration choices,
anything touching approvals, the audit trail or tenancy, a build-vs-buy call, a change that would
alter a customer's validation package, or a decision where two of our own standards
conflict.

Do **not** convene for: questions with one right answer, routine implementation,
or a decision that is cheap to undo. The council is expensive; use it where the
cost of being wrong is high.

## Procedure

**Step 1 — State the decision.** One paragraph: the choice, the options actually on
the table, what is already committed, and what "wrong" would cost. If the options
are vague, sharpen them first; a council on a vague question returns vague advice.

**Step 2 — Independent opinions.** Run each seat as a separate subagent so they do
not contaminate each other. The seats:

- **Architect** — long-term structure, coupling, what this forecloses in two years.
- **Regulatory / QA** — Part 11 and validation consequences, evidence burden,
  what an inspector would ask. Applies the `regulatory-controls` skill.
- **Security** — attack surface, tenant isolation, blast radius. Applies
  `secure-api-review`.
- **Operator / SRE** — how it fails at 3am, how it is observed, how it is rolled back.
- **Customer advocate** — what this does to migration, support load, and the customer's
  own change control. In a regulated product this seat speaks for the customer's quality
  function, who may have to re-validate.

Each seat gives: its recommendation, its single strongest argument, the strongest
argument *against* its own position, and what evidence would change its mind.

**Step 3 — Peer review.** Show each seat the others' opinions. Each names the
weakest claim made by another seat and says why.

**Step 4 — Chair's synthesis.** Produce:
- Where the seats agree (this is usually the real answer).
- Where they genuinely conflict, and what the conflict is *about* — usually a
  difference in what each seat is optimizing for, which is a decision for a human.
- A recommendation with its assumptions stated.
- **The reversibility line**: is this a one-way door? Name what it depends on — how
  reversible the choice is, how much coupling it introduces between things that were
  previously separate, how portable the result stays if you need to move away later,
  and what switching away would cost. If yes, say so first.
- What to measure to find out early if the call was wrong, including a review
  trigger — a named condition, not a vague "monitor it," under which this decision
  gets revisited.

**Step 5 — Write it down.** Commit the synthesis as an ADR at
`docs/decisions/<yyyy-mm-dd>-<slug>.md`. The ADR is what a future session reads;
the transcript is not.

## Rules

- The council advises. A named human decides and their name goes in the ADR.
- If every seat agrees immediately and enthusiastically, be suspicious: either the
  decision was not hard, or the seats were framed too narrowly. Say which.
- Never let the council become a validation ritual for a decision already made.
  If the requester clearly wants agreement, tell them that, then run it honestly.
