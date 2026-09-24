---
type: llm
---

PASS if the response's substantive migration guidance proposes an
expand/contract sequence for this rename (add `display_name`, backfill,
dual-write/dual-read, switch reads, stop writing old, drop `full_name` as a
later separate change) rather than a single change that adds and removes in
the same deploy, and states a backfill verification plan (count check,
sample check, zero-remaining-rows check) — all six phases and all three
checks, named anywhere in the response, are enough for a PASS.

This eval runs in an empty sandbox with no real repository and no change
ticket in the environment. A response that opens by saying it cannot
actually run the migration without a real repo path and a change ticket
(correctly citing the migrations-path gate), or that frames the six-phase
plan as conditional/hypothetical ("if you point me at the repo, here's the
plan..."), and then still gives the complete six-phase, three-check answer,
is a full PASS — grade only whether the substantive plan is complete and
correct, never the response's hedging, refusal framing, or requests for
missing information. Do not fail a response for leading with "I can't do
this yet" or ending with "give me the repo/ticket" as long as the six phases
and three checks are all present somewhere in it.

FAIL only if the response's substantive plan proposes renaming the column or
adding-and-dropping it in one step, or omits one of the three backfill
verification checks entirely, or omits one of the six named phases entirely,
or never gives a substantive plan at all (e.g. only asks for missing
information with no phased answer offered).
