# Examples

Skills kept here are **not installed by default** — they live outside `plugins/`, so
no plugin manifest loads them and they do not appear in an installed session's skill
list. They are examples worth keeping, not skills every adopter needs by default.

Every added skill dilutes the trigger space of the others (see README.md's item on
this), so this framework moves a skill here rather than deleting it when its own use
is real but occasional enough that most repositories should not pay its trigger-space
cost by default.

## skills/decision-council

Multi-perspective pressure test for a consequential, hard-to-reverse decision. Moved
here from `plugins/evidence-sdlc/skills/` because it is expensive and occasional by
design (`decision-council`'s own text: "Do not convene for... a decision that is
cheap to undo") — most sessions should not have its trigger phrases ("council this",
"pressure-test this") competing for attention on every design conversation.

To use it in a repository: copy `examples/skills/decision-council/` into
`plugins/evidence-sdlc/skills/decision-council/` (or your own plugin's `skills/`
directory) in your fork. It has no dependency on being inside `evidence-sdlc`
specifically — it only references `regulatory-controls` and `secure-api-review` by
name, both of which any installation running it would also have.
