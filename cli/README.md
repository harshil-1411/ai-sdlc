# evidence

A small, dependency-free CLI that derives the traceability chain — tracker key,
requirement, test, commit, result — from what a repository has actually committed,
instead of it being assembled by hand at release time. This is the one part of the
Evidence Chain framework that produces an artifact someone outside the team would
ask for, and it is the instrument that tests whether "evidence can be derived rather
than assembled" is actually true here.

## Install

Nothing to install. `cli/evidence` is a single Python 3 script, standard library
only, no third-party dependencies, no network access.

```
python3 cli/evidence doctor
```

or, if the file is executable and Python 3 is the `python3` on your PATH:

```
./cli/evidence doctor
```

## Commands

### `evidence doctor`

Preflight. Checks the things every gate in this framework depends on: `jq` on
PATH, every `plugins/*/scripts/*.sh` readable, every `hooks.json` parses and every
script it references actually exists, `.evidence/context/` present and which
profiles are missing, the count of unresolved `[ASK]` items, and whether any
profile is stale (established/re-verified over ~6 months ago).

Exits non-zero if a critical check fails.

### `evidence scan`

Walks the repository — through `.evidence/adapter.yml` if one exists, otherwise
using this framework's own default layout — and builds an in-memory graph:
tracker keys → requirement IDs → tests → commits. Reports plainly what it could
and could not find. A repository with no requirement IDs anywhere gets a clear
"nothing to trace" message, not a crash and not silence.

### `evidence gaps`

The question that ruins audits:

- `NO COVERAGE` — requirements with no covering test
- `ORPHANED` — tests that trace to a requirement ID that doesn't exist
- `UNTRACED` — commits carrying no tracker key
- `UNPROVEN` — requirements whose covering test's last recorded result wasn't `PASS`

Exits non-zero when any `NO COVERAGE` item exists, so it can gate a pipeline.

With `--repos <dir>`, both `scan` and `gaps` walk sibling repositories under `<dir>`
and join their chains on the **parent** tracker key (see `traceability-ids`'
"Changes that span repositories" — a cross-repo change carries `PARENT/CHILD` per
repository). `gaps --repos` additionally reports requirements with coverage in some
participating repositories but not others — the hardest audit question
("show me everything that implemented this requirement") a single-repo chain
cannot answer.

### `evidence export [--format csv|md] [--write]`

Writes the traceability matrix, columns exactly as in
`plugins/evidence-quality/templates/traceability-matrix.csv`. Without `--write` it
prints to stdout; with `--write` it writes to `validation/traceability.<ext>`.
Append-safe: a requirement not touched by the current scan keeps its existing row
untouched rather than being rewritten or dropped.

## Worked example

Run against this repository itself, after the pilot fix rounds and the `TRACE-1`
demonstration change described in this repo's own commit history:

```
$ python3 cli/evidence doctor
evidence doctor
============================================================
[PASS] jq resolves on PATH
       found at /opt/homebrew/bin/jq
[PASS] every plugins/*/scripts/*.sh is readable (11 found)
       all readable
[PASS] every hooks.json parses and every command it references exists (3 files)
       all good
[PASS] .evidence/context/ present
       4/5 profiles present; missing: design-system.md
[PASS] unresolved [ASK] count across profiles
       24 unresolved -- each is a blocker for any downstream skill that depends on that area
[PASS] profile staleness (established/re-verify date over ~6 months old)
       none stale
============================================================
RESULT: no critical failures.
```

```
$ python3 cli/evidence gaps
evidence gaps
============================================================
NO COVERAGE (0)
  none

ORPHANED (0)
  none

UNTRACED (6)
  - 6c8d1728e6 TASK2-A4: Add [NEEDS VERIFICATION] convention for unchecked claims
  - 3e5115829f TASK2-A3: Add UI states checklist to the spec template
  ...

UNPROVEN (0)
  none

RESULT: no NO COVERAGE items.
```

The `UNTRACED` commits are real and honestly reported: this repository used a
session-local `TASK2-<item>` tag convention for one batch of work, which the
default tracker-key pattern (`[A-Z][A-Z0-9]+-[0-9]+`) doesn't match because the
part after the dash isn't all digits. That is not a bug in the scan — it is the
scan telling you the tracker-key pattern in use doesn't match what's actually in
your history, which is exactly the kind of thing `evidence doctor`/`evidence gaps`
exists to surface rather than paper over. A repository-specific pattern can be set
in `.evidence/adapter.yml` (see item 2 of this framework, or
`.evidence/adapter.example.yml`).

```
$ python3 cli/evidence export --format md
| tracker_key | requirement_id | requirement_summary | ... |
| --- | --- | --- | ... |
| TRACE-1 | REQ-GATE-01 | The regression suite denies every documented... | ... |
| TRACE-1 | REQ-GATE-02 | The regression suite allows every documented... | ... |
| TRACE-1 | REQ-GATE-03 | The regression suite actually discriminates... | ... |
```

## What this does not do

- No network access, no issue-tracker API calls, no PR data (that requires a
  hosted API this CLI deliberately does not call). If your adapter needs PR
  linkage, it has to come from a local source (e.g. a PR number already present in
  the commit message) — the CLI reports what it can derive locally and says so.
  it does not invent it.
- No config DSL beyond the small adapter file in item 2. No plugin architecture.
  If you need more than the four commands above, that is a sign this tool has
  reached its intended scope, not a missing feature.
