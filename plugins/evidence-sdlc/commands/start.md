---
description: Start a tracked change — lifecycle state, branch and the artifacts its risk tier requires
argument-hint: <KEY> [tier 1|2|3] [feature|fix|chore] [short title]
---
Start a change for: $ARGUMENTS

1. If the tier is not given, apply the risk-tiering skill first and state `Risk tier: <n> — <reason>`.
2. Run `evidence change start <KEY> --tier <n> --kind <kind>`. If it reports overlapping claims
   with another active change, stop and tell the human.
3. Create or switch to a branch carrying the key: `git switch -c <kind>/<KEY>-<slug>`.
4. Produce what the tier requires, in order, using the skills: Tier 3 → intent-capture, then
   spec-and-design, then codebase-grounded-planning; Tier 2 → spec-and-design, then planning;
   Tier 1 → planning. For a fix, use root-cause-analysis to write the plan.
5. Finish with `evidence change status <KEY>` and ask the human to review the plan and send
   `/evidence-sdlc:approve <KEY> <plan-sha>`. Never approve it yourself.
