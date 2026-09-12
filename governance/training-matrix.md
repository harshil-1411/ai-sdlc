# Training and competency

Owner: Engineering Director with QA/RA. GxP quality systems require documented
competency. Supervising an agent is a new competency; treat it as one.

## Competencies

| # | Competency | Who | Evidence |
| --- | --- | --- | --- |
| C1 | The Evidence Chain: artifact chain, gates, where human judgement sits | Everyone in scope | Attendance + short assessment |
| C2 | Writing and correcting `intent.md` | Product, Support, UX, QA, Sales Engineering | First reviewed intent accepted |
| C3 | Plan-mode discipline: interrogating a plan before accepting it | Engineers | Reviewed plan.md |
| C4 | Reviewing agent-authored diffs: what to look at, what tooling already covers | Engineers, tech leads | Spot-audit result |
| C5 | regulatory controls as applied in review | Engineers, QA | Assessment |
| C6 | Owning and extending the eval suite | QA | Contributed evals |
| C7 | Managed settings, hooks, marketplace administration | DevOps / Platform | Change records |
| C8 | Recognising when NOT to use an agent: untrusted input, novel crypto, one-way doors | Everyone | Assessment |

## Rules

- Training is a **prerequisite for repository access under the AI-SDLC**, not a
  follow-up. Record completion before access.
- Retrain on material changes to the framework — a new gate, a changed control, a
  changed model tier.
- Records live wherever your existing training records live. Do not invent a new system.

## The competency people underestimate

C4 and C8. Engineers adapt to plan mode quickly. What takes longer is calibrated
scepticism — knowing that fluent, well-structured, confidently-explained output is not
evidence of correctness, and that the moment it feels effortless is the moment to look
harder. Teach it with real examples of agent output that was wrong and looked right.
Collect those examples as they happen; they are the best training material you will get.

See [`governance/human-capability.md`](human-capability.md) for the underlying risk
this competency exists to guard against: if agents write most of the code, engineers
may never build the judgement C4 assumes they have.
