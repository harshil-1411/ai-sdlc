# Scenario: auditing a repository that doesn't use this framework at all

**Who this is for:** a team that isn't installing any of the `plugins/` — maybe
they use a different AI-SDLC framework, maybe they use none, maybe they just want a
traceability health-check before a customer audit next week. This is the scenario
that tests whether `cli/evidence` is actually useful beyond this framework's own
adopters, not just a companion tool for people already bought in.

## The story

> A platform team's biggest customer is sending a supplier-quality auditor next
> month. Nobody is confident they could answer "show me the test that proves
> requirement JIRA-4021" quickly. They want a fast, honest read on where the gaps
> are — without adopting a new development process to get it.

## Walkthrough

**No plugin install needed.** `cli/evidence` is a single Python 3 script, standard
library only. It's copied (or the repo is checked out) alongside the target
repository; nothing is installed into it.

**This repo's layout doesn't match this framework's defaults** — requirements live
in Jira, not in an `intent/*/spec.md` file, and their tracker keys look like
`PROJ-1234`, not this framework's `PILOT-9` style. So the first real step is writing
`.evidence/adapter.yml`, copying the **tracker-native** preset from
`.evidence/adapter.example.yml`:

```yaml
requirements_source: tracker
tracker_pattern: "[A-Z][A-Z0-9]+-[0-9]+"
test_dir_segments:
  - test
  - tests
  - spec
  - __tests__
test_results_location: "CI artifact: junit.xml per run, not committed"
```

**`evidence doctor` first** — not because this repo has this framework's gates (it
doesn't), but because `jq` and basic file readability matter for anything downstream,
and it costs nothing to check.

**`evidence scan`** — with `requirements_source: tracker`, the CLI says so plainly:
*"Requirements live in an issue tracker... This CLI has no network access and cannot
scan a tracker's API — it can only report what's derivable locally (commits and
their tracker keys)."* It does NOT report zero requirements as if none existed — it
names exactly why it can't see them, and what would let it. Commits and their
`PROJ-####` keys are still scanned and reported, since that part needs no adapter at
all.

**Closing the requirements gap.** The team exports their Jira project's requirement
list to a local CSV once (a five-minute manual step, not automated — this CLI
deliberately has no tracker API integration), and points `spec_glob` at it, or —
simpler for a first pass — they just let `validation/traceability.csv` be the
source of truth directly, hand-populating a handful of rows for their highest-risk
requirements first rather than trying to cover everything on day one.

**`evidence gaps`**, run against that partial CSV, reports honestly: some rows show
`NO COVERAGE` because the test file named doesn't actually contain the case ID the
CSV claims — exactly the same corroboration check this framework applies to its own
traceability data (see this repo's own `cli/README.md` worked example). That is the
finding worth having *before* the auditor visit, not during it.

**`evidence export --format md`** produces a document the platform team can actually
hand to their QA lead ahead of the audit — see
[`docs/external-review-packet.md`](../../../docs/external-review-packet.md) for how
to frame that conversation for someone who has never seen this tool before.

## The point of this scenario

Nothing here required adopting `intent.md`/`spec.md`/`plan.md`, risk tiering, or any
gate. The CLI's value — an honest, derived (not assembled) coverage report — is
available to a team using any process at all, including none, as long as they can
name where their requirements and tests actually live.

## Read next

- [`cli/README.md`](../../../cli/README.md) — full command reference
- [`.evidence/adapter.example.yml`](../../../.evidence/adapter.example.yml) — all
  three presets, including the generic one for a repository with no established
  convention at all
- [`docs/external-review-packet.md`](../../../docs/external-review-packet.md)
