---
description: Show where a change stands — stage, missing artifacts, approval, required review agents
argument-hint: [KEY]
---
Run `evidence change status $ARGUMENTS` (with no key it uses the branch's key) and
summarise for the human in a short list: stage, what is missing, whether the plan approval
is valid, which review agents still need to run, and the single next step. If there is no
change yet, say how to start one with `/evidence-sdlc:start`.
