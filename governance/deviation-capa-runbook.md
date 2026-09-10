# Deviation and CAPA: agent-involved defects

Owner: QA/RA. Applies whenever a defect reaches UAT, validation, or production and an
agent authored or materially modified the change.

> An inspector will construct this scenario hypothetically. Have the answer written
> before they do.

## 1. Classification

An agent-authored defect is **not a special category of deviation.** It is classified
by impact on the regulated record, exactly as a human-authored defect would be:

| Class | Definition | Route |
| --- | --- | --- |
| Critical | Regulated record affected: audit trail incomplete/incorrect, signature integrity, record integrity, tenant data crossing, authentication bypass | Immediate deviation record; customer notification assessment within 24h; CAPA mandatory |
| Major | Validated workflow behaves differently from its specification, but records remain intact | Deviation record; customer notification if their validation package asserts the affected behaviour; CAPA mandatory |
| Minor | Cosmetic, performance, or non-validated functionality | Standard defect handling; no deviation record |

Record the agent's involvement as a **contributing-factor field** on the deviation, not
as its classification. This matters: classifying by authorship rather than by impact
would understate human-authored defects and overstate agent ones, and would not survive
review.

## 2. Investigation — the questions specific to agent involvement

1. Which artifact in the chain first contained the error — intent, spec, plan, or diff?
   The chain is committed, so this is answerable rather than reconstructed.
2. Did a control fail, or was there no control? Name it.
3. Did the review that approved it examine the relevant part of the diff? If review
   depth was the failure, that is a **systemic finding**, not an individual one.
4. Was the specification ambiguous? Ambiguous specs are the most common root cause and
   the cheapest to fix.
5. Would an existing skill have caught it had it triggered? If yes, why did it not
   trigger?

## 3. Mandatory CAPA outputs

Every Critical or Major deviation produces, at minimum:

- **A permanent eval.** The failure case joins the evaluation suite so the configuration
  is tested against that class from then on. This is the single highest-value CAPA
  action available and it should be default.
- **A `CLAUDE.md` or skill correction**, where the root cause was missing context.
- **A hook**, where the root cause was a policy that must hold without exception and
  currently only had advisory enforcement.
- **A risk-tier review**, where the root cause was insufficient human review depth.

## 4. Customer notification

Trigger assessment when: the defect affects a behaviour the customer's validation
package asserts, or any regulated record was affected. Notification content is decided
by QA/RA with Legal. Customers need enough to assess their own validated state.

## 5. What must never happen

- The agent that authored the defective change must not be the sole author of its fix
  review. Fresh context, and a human owner.
- A deviation must not be closed on the strength of "the agent has been instructed not
  to do that again." Instructions are advisory. The CAPA must land in an eval, a hook,
  or a test.
