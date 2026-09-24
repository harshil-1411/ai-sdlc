---
description: Start a tracked change — lifecycle state, branch and the artifacts its risk tier requires
argument-hint: <KEY> [tier 1|2|3] [feature|fix|chore] [short title]
---
Start a change for: $ARGUMENTS

1. If the tier is not given, apply the risk-tiering skill first and state `Risk tier: <n> — <reason>`.
2. Create or switch to a branch carrying the key, in its own Bash call:
   `git switch -c <kind>/<KEY>-<slug>`.
3. Run `evidence change start <KEY> --tier <n> --kind <kind>` as its own command (a `cd` before it
   is fine). The gate engine performs it and signs the change state. The call comes back as a
   denial that begins "Done by the gate engine", which is the success message. Chained with any
   other program, it is refused. If it reports overlapping claims with another active change,
   stop and tell the human.
4. Produce what the tier requires, in order, using the skills: Tier 3 → intent-capture, then
   spec-and-design, then codebase-grounded-planning; Tier 2 → spec-and-design, then planning;
   Tier 1 → planning. For a fix, use root-cause-analysis to write the plan.
5. Finish with `evidence change status <KEY>` and ask the human to review the plan and send
   `/evidence-sdlc:approve <KEY> <plan-sha>`. Never approve it yourself.
