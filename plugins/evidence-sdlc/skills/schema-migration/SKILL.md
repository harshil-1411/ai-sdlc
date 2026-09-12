---
name: schema-migration
description: Design and review data-model migrations safely — expand/contract phasing, backfill verification, tested rollback, and the regulated-record integrity checks a normal code review misses. Use whenever anyone says "migration", "alter the schema", "add a column", "change the data model", "backfill", "rename a field", "drop a table", "reindex", and on any edit under a migrations directory. Migrations are the highest-consequence change type in most systems — hard to test, expensive to reverse, and they touch record integrity directly.
---

# Schema migration

`protect-validated-paths` gates a `migrations/` directory and stops there — it
enforces that a change ticket exists, but says nothing about whether the migration
itself is safe. This skill is that missing guidance.

## Rule 0 — expand-contract is the default

Never combine adding and removing in one deployable change. The default sequence,
each phase its own deployable change:

1. **Expand** — add the new column/table/field. Nothing reads it yet.
2. **Backfill** — populate the new structure from the old.
3. **Dual-write / dual-read** — new code writes both; reads can go either way.
4. **Switch reads** — application code reads from the new structure only.
5. **Stop writing old** — the old structure is now dead weight, not yet gone.
6. **Contract** — remove the old structure.

If you are asked to "just add a column and switch to it," that request is asking for
steps 1 and 4 to happen in the same change. Say so, and propose the phased version
instead — do not silently comply with a plan that skips backward compatibility.

## Rule — the backward-compatibility window

During any rolling deploy, the previous release's code and the new release's code run
simultaneously against the same schema. Every migration must be safe for the
**previous** release to keep running against the **new** schema, for the full
duration of the rollout — not just safe for the release that introduced it. A column
made `NOT NULL` before every writer has been updated to supply it is a production
incident waiting for the next deploy, not this one.

## Rule — backfill verification

Never assume a backfill completed. A backfill is not done until all three are true,
and each is checked, not asserted:

- **A count check** — the number of rows migrated matches the number expected.
- **A sample correctness check** — spot-check actual values, not just row counts;
  a backfill can move the right number of wrong values.
- **A query proving zero remaining unmigrated rows** — run it, don't infer it from
  the job's exit code.

State the runtime estimate for the backfill and whether it locks the table (or rows)
while running. A backfill that locks a hot table is itself a production-risk decision,
not an implementation detail to skip past.

## Rule — rollback is tested before the forward migration runs, not after

A down-migration that has never been run is not a rollback plan — it is an untested
guess written at the same time as the mistake it is meant to undo. Run it, on a copy
of representative data, before the forward migration is applied anywhere real.

Some migrations are genuinely irreversible (a dropped column whose data is gone, a
type-narrowing that lost precision). Say so explicitly rather than writing a
down-migration that would not actually restore the prior state. A stated
irreversibility is honest; a fictional down-migration is a false sense of safety.

## Rule — regulated records

This is the part a normal code review misses. If the table touched holds a regulated
record, apply the `regulatory-controls` skill and verify, explicitly, that after the
migration:

- **Historical records remain retrievable and unaltered.** A migration is not allowed
  to silently change what a past record says.
- **Any integrity hash, seal, or signature still verifies.** If the migration touches
  a column that is part of a signed or hashed payload, the signature breaks unless
  the migration is designed around it — this is a common, expensive mistake.
- **The audit trail for migrated records is preserved, not regenerated.** The
  migration is not an opportunity to "clean up" old audit history.
- **The migration itself is an auditable event** — who ran it, when, and against
  what environment, recorded the same way any other action on a regulated record is
  recorded.

A migration touching a regulated table is **Tier 3 by definition**, per
`risk-tiering`. Being provably behaviour-preserving does not reduce this tier — that
reduction rule exists for code refactors, not for changes to the data a regulated
record's integrity depends on.

## Rule — a destructive step is its own change

Refuse to generate a destructive migration (drop column, drop table, truncate, a
type-narrowing cast) in the same change as anything else — including the expand
phase of the same broader migration. State plainly that the destructive step is its
own change, sequenced after the contract phase has been live long enough to be
confident nothing still depends on the old structure, with its own review and its
own approval. A destructive step bundled with unrelated work is a destructive step
nobody specifically approved.

## Output

A migration proposal states, in order: which expand-contract phase this change is,
the backward-compatibility argument for this phase specifically, the backfill
verification plan (or "no backfill needed" with why), the rollback plan (tested, or
explicitly irreversible with why), the regulated-record checks above (or "not a
regulated table" with why), and the risk tier.
