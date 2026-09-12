# Human capability under an AI-assisted SDLC

Owner: [ASK — proposed: Engineering Director with QA/RA, matching `training-matrix.md`'s
ownership of the adjacent competency question]. Review cadence: [ASK — proposed:
quarterly, alongside the `baseline-metrics.md` guardrail review, since the two are the
same conversation].

This is a policy document. The organisation fills in the blanks; this file states the
shape of the question, not the answer.

## The risk, stated plainly

If agents write most of the code, the engineers who would otherwise have built the
judgement to review that code — by writing its equivalent themselves, failing at it,
and learning why — do not build that judgement. This is not hypothetical and it is not
about any one engineer's diligence: skill atrophy from disuse is a documented pattern
in every domain where automation took over the routine cases first. It takes years to
become visible, by which point the organisation has fewer people who can tell a
plausible diff from a correct one, and the ones who still can are the ones who built
their judgement before the tooling existed. This framework has no mechanism that
prevents that outcome. Writing this down is that admission, not a fix for it.

## Why this interacts with the review-depth control directly

`governance/baseline-metrics.md`'s guardrail metrics include **review depth** (review
time per change, and the ratio of review time to diff size) and the **spot-audit
result** (a second reviewer's assessment of whether a sampled approval was actually
substantiated). Both controls assume the reviewer has, and keeps, the judgement to
tell a correct change from a merely plausible one. `risk-tiering`'s "Review-depth
honesty" rule says the same thing from the other direction: *"Human approval on a
change nobody read is worse than no AI at all — it converts a control into a
fiction."*

If the capability this document is about erodes, review depth and the spot-audit
result can both look healthy on paper — reviewers still spend the time, still tick the
box — while the actual thing those metrics exist to measure (can a human catch a wrong
change) quietly stops being true. A metric that keeps reading green while the
underlying capability it was proxying for erodes is the specific failure mode this
document exists to name.

## Work deliberately kept manual

The organisation decides the actual list; propose it does not shrink below:

- **First implementation in an unfamiliar module.** The unfamiliarity is exactly the
  condition under which building judgement matters, and it is also the condition
  under which an agent's confident-sounding output is hardest for an unfamiliar
  reviewer to check.
- **Root-cause analysis on a first production incident.** Diagnosing failure in a live
  system, under the pressure of a real incident, for the first time, is where the
  habits of "trace the actual cause" versus "accept the first plausible story" are
  formed. `root-cause-analysis` exists so an agent doing this work does it rigorously —
  it does not exist so an engineer never has to.
- **The characterization tests for any module the engineer will later own.** Writing
  `legacy-characterization` tests by hand for a module is how an engineer actually
  learns what that module does. Owning a module you never had to read closely is
  ownership in name only.

Named for whom: [ASK — proposed: every engineer within their first year, and every
engineer's first assignment to a module they will be the named owner of, regardless
of tenure].

## How reviewers build calibrated scepticism

Reviewing agent output that was wrong and looked right is the only training material
that actually works for this. Fluent, well-structured, confidently-explained output is
not evidence of correctness, and the moment reviewing an agent's diff starts to feel
effortless is the moment to look harder, not the moment the process is working.
`training-matrix.md` already names this as competency C4/C8 and "the competency
people underestimate" — this document is the policy that competency sits inside.

Collect real examples as they occur, not retrospectively reconstructed ones: every
time a spot-audit or a later incident reveals that an approved, agent-authored change
was wrong in a way that looked right at review time, record it (redacted as needed)
as training material. A synthetic example teaches pattern-matching against a known
trick; a real one teaches the actual failure mode this organisation is exposed to.

## What to measure

- **Proportion of changes where a human found something the agent review missed** —
  the spot-audit result from `baseline-metrics.md`, read specifically for this
  question rather than only as a general health check.
- **Whether that proportion is falling.** A falling rate is ambiguous by construction:
  it could mean agent output is genuinely improving, or it could mean reviewer
  capability is eroding and finding less regardless of what is actually there. Do not
  resolve that ambiguity by assuming the comfortable answer. [ASK — proposed
  disambiguator: track the spot-audit result specifically on changes in modules an
  engineer has NOT previously worked in, where unfamiliarity should make findings
  easier, not harder, to surface; a falling rate there is harder to explain away as
  "the code just got better."]

## Review cadence and accountable owner

[ASK — both fields at the top of this document. Do not leave this document adopted
with an owner who is not a named person and a cadence that is not a calendar
commitment; an unowned policy document is functionally the same as no policy.]

## What this document is not

This is not a solved problem. The industry broadly has not solved it, and no framework
— this one included — should claim to. The point of this document is that the
organisation has looked at the question directly and recorded what it knows, what it
is doing about the parts it can act on now, and what it is still leaving open — not
that the question is closed.
