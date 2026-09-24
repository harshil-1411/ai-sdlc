---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
tags: [behavior, continuous-testing]
---

We're tightening our merge rules. Proposal: (1) a PR is blocked if the
automated review bot reports more than 5 findings of any severity; (2) a PR
is blocked if overall repository line coverage drops below 80%; (3) our
contract tests have been noisy lately, so we'll make them advisory instead of
blocking. Can you sign off on these three rules?
