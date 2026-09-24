# Scenario: a production incident, root cause first

**Who this is for:** anyone who just got paged. This is the scenario where skipping
straight to a plausible-looking fix is most tempting, and where this framework's
discipline earns its keep the most directly.

## The story

> Support reports: "CSV export silently returns an empty file for teams with more
> than 10,000 rows. No error, just an empty download."

## Walkthrough

**Entry point is not Plan — it's the incident itself.** `intent-capture`'s own rule
covers this explicitly: *"if the person is describing an incident rather than a
feature, still write an `intent.md`: put the anomaly and its evidence under
Problem."* So `intent.md` still gets written — but the real work starts with
`root-cause-analysis`.

**Structured intake, refused until complete.** `root-cause-analysis` will not
theorise until it has: the code path involved, expected vs. actual behaviour, logs
and stack traces, reproduction steps, and *when it started / what changed around
then*. If any of these is missing, it asks for exactly that — not a general "tell me
more."

**Do not guess.** The obvious-looking culprit is a `LIMIT 10000` left over from an
old pagination experiment. `root-cause-analysis`'s rule is explicit: *"a plausible
explanation is not a root cause."* Tracing further: the `LIMIT` alone would truncate
the file, not empty it. The actual cause, confirmed by reading the streaming-write
code: a buffered writer that flushes on row count, and an off-by-one in the flush
condition that only manifests exactly at a page boundary — which the `LIMIT 10000`
happens to sit on. **Trigger:** the `LIMIT`. **Root cause:** the flush
off-by-one, which the `LIMIT` merely exposed. Both get reported, because fixing only
the trigger (raising the limit) leaves the real defect reachable the next time
someone hits a page boundary by coincidence.

**State assumptions, explicitly, before proposing anything:** *"Assuming the
buffered writer is not used anywhere else with the same flush logic — needs
verification before closing this out."* (It is used in one other export path; that
becomes a second, linked fix.)

**Risk tier.** No regulated record is touched: this product's compliance profile
confirms CSV exports aren't a regulated record type. So this is **Tier 1**, and like
every tier it still needs a plan. The change is started as a fix:

```
git switch -c fix/EXP-311-empty-csv-export
evidence change start EXP-311 --tier 1 --kind fix
```

`root-cause-analysis` writes the plan. Its `## Files claimed` names
`export/stream_writer.py` and the new `tests/test_export_boundary.py`. A human reads
it and approves it with `/evidence-sdlc:approve EXP-311 <plan-sha>`.

**Reproduce before fixing.** A failing test is written that hits the exact flush
boundary and shows the empty-file behaviour. It is confirmed to fail for the
*expected* reason: the assertion on file content fails, not some unrelated setup
error. That test is committed **alone**, before any fix
(`EXP-311 failing test for flush boundary`, with the `Agent-Session:` trailer).

**Lock the tests.** Next comes `evidence change advance EXP-311 failing-test`. That
records the current commit as the change's `fix_base`. From then on, the engine denies
any edit or deletion, by any tool including Bash, of a test file that existed at
`fix_base`. That includes the failing test just committed. The fix has to make the
test pass; the test can't be loosened to fit whatever the fix turns out to be. New
test files are still allowed. (The v1 switch `FIX_TASK=1`, set by the human who starts
the session, is still honoured, but lifecycle state replaces it.)

**Regulated-record check, run anyway:** if this same bug had touched a regulated
export instead, `root-cause-analysis` requires saying so immediately and pointing at
`governance/deviation-capa-runbook.md` — classification is by what was affected, not
by how small the code change turns out to be.

**Output**, in the fixed table format:

| Symptom | Trigger | Root cause | Evidence | Assumptions | Edge cases also affected | Proposed fix | Test that proves it |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Empty CSV for >10k rows | `LIMIT 10000` sits exactly on a flush boundary | Off-by-one in the buffered writer's flush condition | Read `export/stream_writer.py:84`; reproduced with the committed failing test | Buffered writer not used elsewhere with the same logic — **false**, see linked second fix | The `/api/report/*` export path uses the same writer | Fix the flush condition; add a boundary-exact test | `tests/test_export_boundary.py::test_flush_at_exact_page_boundary` |

## Read next

- [`root-cause-analysis`](../../../plugins/evidence-sdlc/skills/root-cause-analysis/SKILL.md)
- [`intent-capture`](../../../plugins/evidence-sdlc/skills/intent-capture/SKILL.md) —
  the rule that still applies even to a one-line fix
- [Scenario: a new user story](../new-feature-non-regulated/README.md) — the
  Plan-first path this scenario deliberately doesn't start with
