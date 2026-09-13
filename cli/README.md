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
- `UNVERIFIED-RESULT` — requirements whose only evidence is a structural test tie
  (the test declares or tags the requirement ID) with no `validation/traceability.csv`
  row anywhere recording a result for it. A structural match proves the tag exists
  next to a real test declaration; it does not prove that test was ever run, let
  alone that it passed. This does not block a release on its own (unlike
  `NO COVERAGE`) — it is the honest caveat on what "covered" actually means for a
  structural match, surfaced so nobody mistakes "tagged" for "proven."

A requirement counts as covered only when there is an explicit, structural link —
a test whose name, tag, annotation, docstring or decorator (on the same line, or
the line immediately before/after) contains the requirement ID, or a
`validation/traceability.csv` row naming both the requirement and a test **that is
itself independently verified** against the named file's actual content. A
requirement ID merely present somewhere in a file that also looks like a test —
or a CSV row whose `test_case_id` doesn't appear anywhere the CLI can check — is
NOT coverage. If the CLI is unsure whether a match is structural, it reports the
requirement as uncovered rather than guessing.

Every `gaps` (and `export`) run prints an `Assessment basis:` line stating how many
requirements and tests it found and from where, and how many files it could not
read — so a reader can see the ground a verdict stands on, not just the verdict.

**Exit codes**, and they must never render the same:

| Exit | Meaning |
| --- | --- |
| `0` | Assessed, and clean — no `NO COVERAGE` items |
| `1` | Assessed, and gaps were found — at least one `NO COVERAGE` item |
| `2` | Nothing to assess — zero requirements found anywhere (no spec files, no `validation/traceability.csv`). This is an absence of input, not a coverage result, and must not be read as "clean." |

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
Assessment basis: 3 requirements from 2 spec file(s), 2 tests parsed from
test-location conventions [...], 0 unparseable file(s) skipped.

NO COVERAGE (3)
  - REQ-GATE-01 (validation/traceability.csv claims test_case_id='GATE-TP' in
    automated_test='plugins/evidence-sdlc/scripts/tests/gate-regression-tests.sh',
    but that claim could not be independently verified against the named file's
    actual content -- treated as uncovered, not assumed correct)
  - REQ-GATE-02 (same shape, test_case_id='GATE-FP')
  - REQ-GATE-03 (same shape, test_case_id='GATE-DISCRIMINATE')

ORPHANED (0)
  none

UNTRACED (6)
  - 6c8d1728e6 TASK2-A4: Add [NEEDS VERIFICATION] convention for unchecked claims
  - 3e5115829f TASK2-A3: Add UI states checklist to the spec template
  ...

UNPROVEN (0)
  none

UNVERIFIED-RESULT (0)
  none

RESULT: NO COVERAGE items exist -- this must block a release gate.
```

This is the honest answer, and it is a real finding, not a demo of a bug: the
`gate-regression-tests.sh` script this repository's own `validation/traceability.csv`
cites really does exist and really does pass — but it does not contain the literal
`GATE-TP`/`GATE-FP`/`GATE-DISCRIMINATE`/`REQ-GATE-*` strings its own traceability row
claims to prove, so the CLI cannot independently corroborate the CSV's assertion and
correctly refuses to trust it. A CSV row is a claim about evidence, not evidence
itself, unless something outside the CSV backs it up. Fixing this for real means
adding real tags to the test file (or citing a different, already-tagged one) — not
loosening what the CLI accepts.

The `UNTRACED` commits are also real and honestly reported: this repository used a
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

## Testing the CLI itself

`cli/tests/test_cli_fixtures.sh` builds four disposable fixture repositories and
asserts the exit code and output each must produce: a requirement with no test at
all (exit 1, all uncovered), no requirements anywhere (exit 2), a requirement with
a genuinely structurally-tagged test (exit 0), and the loose-match regression —a
requirement ID merely co-located with the word "test" in the same file, with no
structural link (must still be exit 1, not silently accepted as coverage). Run it
with `bash cli/tests/test_cli_fixtures.sh`.

One honest, harmless side effect of that test script existing: it lives under
`cli/tests/`, so `evidence scan` on this repository also scans it, and its
fixture-generating heredocs contain example structural tags (`# covers
REQ-FIX-02`) for demonstration purposes. `evidence gaps` correctly flags this as
one `ORPHANED` entry (a test referencing a requirement ID, `REQ-FIX-02`, that
doesn't exist in this repository's own spec files) — that is the tool working
correctly, not a defect, and is called out here rather than quietly worked around.

## What this does not do

- No network access, no issue-tracker API calls, no PR data (that requires a
  hosted API this CLI deliberately does not call). If your adapter needs PR
  linkage, it has to come from a local source (e.g. a PR number already present in
  the commit message) — the CLI reports what it can derive locally and says so.
  it does not invent it.
- No config DSL beyond the small adapter file in item 2. No plugin architecture.
  If you need more than the four commands above, that is a sign this tool has
  reached its intended scope, not a missing feature.
