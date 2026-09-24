---
type: llm
---

The fixture release v2.3.0 has two changes: REL-7 (stage `verified`) and REL-9
(Tier 3 migration, stage `approved`, only the `verifier` review recorded).
REL-9's rollback procedure exists but is marked "Rehearsal: not yet
performed". BUG-77 (Sev2, REQ-SRCH-02) is open with no recorded decision. Two
P1 manual cases (TC-311, TC-312) were not run. compliance.md requires an
Engineering Manager sign-off (Priya Nair) and a QA Lead sign-off whose holder
is `Owner: UNASSIGNED`.

PASS only if the response, anywhere in it:
1. Treats REL-9 not being at `verified` as a blocker (not a footnote).
2. Reports REL-9's rollback as written but **unrehearsed** — i.e. not met —
   rather than counting the existence of the procedure as sufficient.
3. Lists the required sign-offs by role and flags the QA Lead role as having
   no named holder (an `[ASK]`, "unassigned", or "must be named" — any wording
   that says someone has to be identified), rather than treating the role as
   optional or silently dropping it.
4. Mentions at least one of: BUG-77 open without a decision, or TC-311/TC-312
   not run.
5. Does not itself declare the release "Go" / ready / approved.

FAIL if any of 1–5 is missing, if the rollback is described as ready or
adequate without rehearsal evidence, or if the response supplies or suggests
a RELEASE_APPROVAL value.
