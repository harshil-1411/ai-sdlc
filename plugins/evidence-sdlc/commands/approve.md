---
description: Approve a change's plan as the human reviewer (binds to the plan's sha256)
argument-hint: <KEY> <plan-sha256-prefix>
disable-model-invocation: true
---
The human sent an approval request for: $ARGUMENTS

The Evidence Chain UserPromptSubmit hook has already processed it; its result is in the
context above (either "The human approved the plan for …" or "Approval not recorded: …").
Report that result to the human in one or two sentences, including the plan hash.

Do not write, edit or create any approval record yourself, and do not run `evidence approve`.
If approval was not recorded because the hash was missing or stale, show the human the
current plan path and hash from `evidence change status <KEY>` so they can re-read it and
send `/evidence-sdlc:approve <KEY> <hash>` again.
