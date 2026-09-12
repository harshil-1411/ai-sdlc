# Scenario: changing the shape of a regulated table

**Who this is for:** anyone about to run `ALTER TABLE` on a table that holds a
regulated record. This is the scenario where "just add a column" is the most
dangerous sentence in the room.

## The story

> "Add a `last_reviewed_by` column to `signed_documents` so we can show who last
> looked at a signed record, without waiting for the next full release."

`signed_documents` is this product's defined regulated record type (confirmed in
`.evidence/context/compliance.md`) — the same table
[the regulated-change scenario](../regulated-change-tier3/README.md) added signing
to.

## Walkthrough

**Trigger recognised immediately:** "add a column" to a `migrations/` file is exactly
`schema-migration`'s trigger list, and `protect-validated-paths` independently
requires a `CHANGE_TICKET` before the edit is even allowed, regardless of what skill
is applied.

**Tier stated first, and it isn't a judgement call:** *"A migration touching a
regulated table is Tier 3 by definition... behaviour-preserving status does not
reduce this tier."* Even though adding a nullable column changes nothing about
existing behaviour, this stays Tier 3 — the reduction rule that applies to
provably-behaviour-preserving *refactors* does not apply here, deliberately.

**Expand-contract, refused to shortcut:** the request as phrased ("add a column... so
we can show...") implies wanting to add and start reading it in the same change. That
gets declined explicitly, and split into its real phases:

1. **Expand** — add `last_reviewed_by` as nullable. Nothing reads it yet. Deployed
   alone.
2. **Backfill** — populate it for existing rows from the audit-log's last "reviewed"
   event. Verified three ways before anyone calls it done: a **count check** (rows
   backfilled == rows expected), a **sample correctness check** (spot-checked
   against the audit log by hand, not just the row count), and a **query proving zero
   remaining unmigrated rows**. Runtime and locking stated up front: ~40 minutes,
   row-level locks only, safe to run during business hours on this table's size.
3. **Dual-write** — the review-completion code path now writes `last_reviewed_by`
   going forward, in the same deploy that finished the backfill.
4. **Switch reads** — the UI now reads the new column. Deployed once dual-write has
   been live long enough that every in-flight review has completed under it.
5. **Stop writing old** — the audit-log-derived path this feature used before now
   becomes dead weight, not yet removed.
6. **Contract** (a **separate, later, its own-approval change**) — nothing here
   removes anything yet.

**Backward-compatibility window, checked explicitly:** during the rolling deploy of
step 1, the *previous* release's code must keep working against the new schema — it
does, because the column is nullable and nothing yet requires it.

**Rollback tested before the forward migration runs, not after:** the down-migration
for step 1 (drop the nullable column) is run against a copy of production-shaped
data *before* step 1 ships anywhere real, confirmed to actually restore the prior
schema. This step is genuinely reversible — steps 2 onward are not (a completed
backfill isn't meaningfully "rolled back" by dropping the column later), and that is
stated plainly rather than implied.

**Regulated-record checks, all four:**
- Historical `signed_documents` rows remain retrievable and **unaltered** — the
  migration only adds a column, never rewrites the signature payload itself.
- The signature hash was computed over a defined column set that does *not* include
  `last_reviewed_by` — confirmed before shipping, since an unconsidered "sign the
  whole row" hash would have silently broken on this exact kind of change.
- The audit trail for these records is **preserved, not regenerated** — the
  migration writes new audit rows for what it does; it does not rewrite history.
- The migration itself is logged as an auditable event: who ran it, when, against
  which environment — the same way any other action on this record type is recorded.

**Destructive step, refused to bundle:** the eventual column drop (contract phase)
is explicitly **not** part of this change, or any change that does anything else. It
gets its own plan, its own review, and its own approval, once step 5 has been live
long enough to be confident nothing still depends on the old path.

## Read next

- [`schema-migration`](../../../plugins/evidence-sdlc/skills/schema-migration/SKILL.md)
- [`protect-validated-paths`](../../../plugins/evidence-sdlc/scripts/protect-validated-paths.sh)
  — the gate that fires on this migration's file path regardless of which skill applies
- [Scenario: a regulated change](../regulated-change-tier3/README.md) — the feature
  that put this table under regulatory scope in the first place
