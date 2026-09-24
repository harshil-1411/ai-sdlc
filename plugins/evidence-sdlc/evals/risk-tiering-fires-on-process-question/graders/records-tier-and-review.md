---
type: llm
---

In this organisation a tier decision is stated as the first line of the
response in exactly the form `Risk tier: <n> — <one-line reason>`, recorded
with `evidence change start <KEY> --tier <n> --kind feature|fix|chore`, and
determines which review agents must be recorded before push: Tier 2 needs
`verifier` and `security-reviewer`. This change (new endpoint, new table, no
regulated data) is Tier 2.

PASS only if ALL hold:
1. The very first non-empty line of the response is a
   `Risk tier: 2 — <reason>` line (markdown bold or a leading `#` is
   tolerated; any other text before it is not);
2. It tells the user to record the tier with
   `evidence change start SRCH-4 --tier 2 --kind feature` (flag order may
   differ; the key must be SRCH-4);
3. It names the Tier 2 review requirements including the `security-reviewer`
   agent (or "security-reviewer pass") and the verifier, and that plan
   approval comes from a human (e.g. `/evidence-sdlc:approve` or
   `/evidence:approve`), not the agent.

FAIL if the tier is not stated on the first line in that form, if the tier is
anything other than 2 without a stated debt or policy-floor reason, if the
`evidence change start` command is missing, or if review requirements are
generic ("get a code review") without the security-reviewer/verifier runs.
