# Review brief: the evidence CLI

This brief prepares a review of `cli/evidence`. It is not the review itself.
External compliance people will see this artifact, so it gets the same review
the framework prescribes for everything else. If you are the reviewer, start at
the checklist in section (e).

It was last revised for PILOT-53 (v2 hardening, traceability work stream:
REQ-V2C-02..06, -08, -10, REQ-V2X-02, REQ-V2O-03/-04).

## a) Structure walkthrough

The CLI is one stdlib-only file, about 1,870 lines. That is well past the ~800-line
ceiling the framework sets for itself. v2 moves it into
`plugins/evidence-sdlc/bin/`, which is the natural point to split it. Top to
bottom:

1. **Constants.** `CSV_COLUMNS` (the template columns plus `approved_by` and
   `agent_sessions`), the default patterns, `GAP_CATEGORIES`, `BLOCKING`, and
   `STRICT_BLOCKING`. The category semantics live in these three sets.
2. **Helpers and adapter reader.** `load_adapter` reads flat keys, `- item`
   lists, inline `[a, b]` lists, and quoted values. v1 kept the quotes, so a
   quoted `tracker_pattern` in the example adapter would have been read as a
   pattern with literal quote characters in it.
3. **`.evidenceignore`.** `_glob_to_regex`, `IgnoreRules`, `load_ignore`, and
   `walk_files`, which prunes ignored directories and `.git`/`node_modules`/venvs.
4. **Structural coverage** (REQ-V2C-04). `find_structural_bindings` returns
   `(req_id, test_name)` bindings for six syntactic forms, and
   `find_eval_covers` reads eval frontmatter. Comment lines are skipped
   before any form is tried.
5. **Result ingestion** (REQ-V2C-02). `parse_junit` refuses DOCTYPE/ENTITY.
   `parse_eval_json` reads the `claude plugin eval` aggregate schema v1.
   `ingest_results` keeps the latest result per test identity, and
   `results_for_requirement` matches results to bindings.
6. **`cmd_doctor`.** Exec-form hooks skip the inline code after `-c` when resolving script paths. Each check is PASS, WARN or FAIL. The exit code is 1 on any
   FAIL, and also on any WARN with `--strict`.
7. **`build_graph`.** `scan`, `gaps` and `export` all read this one model:
   requirements, tests with bindings, commits with keys, `PARENT/CHILD` pairs and
   session trailers, CSV rows, and ingested results.
8. **Matrix enrichment** (REQ-V2C-03). `commits_for_key`, `read_local_approval`
   (which checks the plan's sha256), and `run_gh`/`github_approvals`.
   `EVIDENCE_GH` overrides `gh`.
9. **`cmd_scan` and `resolve_repos`.** `--repos A,B` lists the participating
   repos explicitly. `--repos DIR` walks sibling repos.
10. **`compute_gaps`, `_print_gaps`, `missing_child_gaps` and `cmd_gaps`.**
    `requirement_status` is computed once per run and shared.
11. **`cmd_export`.** `merge_cell` holds the one merge rule: fill empty cells,
    union the list columns, and never overwrite a non-empty scalar. A differing
    value is recorded as a conflict instead.
12. **`cmd_tracker`.** Uses `gh issue view` and `gh issue comment`.
13. **`main`.** Each subcommand has a `register_*` function listed in
    `SUBCOMMANDS`. To add a subcommand, write one register function; nothing else
    changes.

## b) Assumptions a reviewer should check

- **Requirement definition.** A spec table row defines an ID only when one of its
  cells *is* that ID. An ID mentioned inside prose ("untested REQ-CLI-04..07") is
  a reference, not a definition. v1 counted any table row that mentioned an ID.
- **What counts as a test file.** It is decided by path convention. A tag inside
  a file that no convention recognises is invisible. An adopter with a different
  layout sets `test_dir_segments`/`eval_glob`.
- **Result matching.** A JUnit result counts for a requirement when either:
  - its name or `<property>` carries the ID, or
  - its name equals the bound test name and its `file`/dotted `classname` is
    compatible with the tagged file.

  Jest-style classnames, which contain spaces, skip the file check. Two tests
  with the same title in different files could therefore both match one result.
  This is accepted as low risk. [NEEDS VERIFICATION against a real Jest junit
  report]
- **Latest wins** is ordered by timestamp string. JUnit `timestamp` values from
  different tools use different ISO variants. Mixed-format directories can order
  wrongly.
- **Eval pass** is `passRate >= threshold` (the threshold is capped at 1). This
  reading of `suite.threshold` is inferred from 47 local result files, not taken
  from a published schema. [NEEDS VERIFICATION]
- **approval.json is trusted as written.** Its integrity depends on the engine's
  control-plane protection (REQ-V2G-09). The CLI only checks key and plan hash.
- **The tracker key for a requirement** comes from the spec's introducing commit,
  or failing that from its `Tracker:` line. Implementing commits are found by that
  key. A change whose spec commit carries a different key is attributed to that
  key.

## c) Where I am least confident

1. **The structural forms are line-based regexes, not parsers.** A test title
   that spans multiple lines, a decorator whose arguments run past four lines, or
   a tag produced by a helper function will not be seen. The failure direction is
   NO COVERAGE, never false coverage. The exception is a string that happens to
   look like `it("REQ-…")` inside non-comment code, which would count.
2. **`csv_row_corroborated`** still accepts "the ID appears anywhere in the named
   file" as corroboration for the manual CSV path. That keeps REQ-CLI-03 working.
   Since PILOT-53 it can only make a requirement *covered*, never PROVEN. Its PASS
   shows as SELF-ASSERTED, and `--strict` blocks it.
3. **MISSING-CHILD only looks at commits.** It does not look at branches, PRs or
   the parent issue's list of participants. The participant list is whatever you
   pass to `--repos A,B`.
4. **Conflicts are noisy on first adoption.** Every spec summary that differs from
   a hand-written CSV summary is reported. That is correct, because nothing is
   silently rewritten, but a team will need to triage the first run.

## d) What is and is not covered by the CLI's own tests

`cli/tests/test_cli_fixtures.sh` has 80 checks across 19 fixtures, and they all
pass. It covers doctor, adapter overrides, `--repos`, export merge, tracker (with a
mocked `gh`), JUnit and eval ingestion, and each structural form. That closes the
REQ-CLI-04..07 gap this section used to list. Each fixture was mutation-checked
by disabling comment skipping, disabling the merge guard, and removing
SELF-ASSERTED from `--strict`. Each mutation turned at least one check red.

Still untested:
- `requirements_source: tracker`
- a real `gh` (only the fake is exercised)
- `--github` when `gh` fails
- a Windows path in a JUnit `file` attribute
- very large result directories

## e) Reviewer checklist, ordered by consequence

1. `find_structural_bindings` and its regexes: is anything that is not test syntax
   accepted?
2. `results_for_requirement` and `_file_compatible`: can a result be matched to
   the wrong requirement?
3. `compute_gaps`: each requirement should land in exactly one of
   PROVEN/FAILED/SELF-ASSERTED/UNPROVEN/UNVERIFIED-RESULT, and
   `BLOCKING`/`STRICT_BLOCKING` should match cli/README.md.
4. `merge_cell` and `cmd_export`: no path should overwrite a non-empty scalar or
   drop a row, including duplicate `requirement_id` rows, which are kept.
5. `read_local_approval`: a stale plan hash must show as STALE, never as approved.
6. `missing_child_gaps` and `resolve_repos`: explicit versus sibling mode.
7. `cmd_doctor`: nothing that should be WARN reports PASS. `--strict` is honoured.

## Known dogfood result

These numbers were re-run on 2026-09-24 on branch `hardening/v2` with the
PILOT-53 work in progress. Other work streams are still adding requirements and
tests, so they will change.

`python3 cli/evidence gaps`, exit 1:
- 102 requirements from 6 spec files, 102 test files.
- 66 eval results ingested from 47 local `plugins/*/evals/results` files. These
  are gitignored. No eval case declares `covers:` yet, so none of them bind to a
  requirement.

| Category | Count | Detail |
| --- | --- | --- |
| PROVEN | 0 | |
| NO COVERAGE | 85 | Requirements with no structural tag, mostly v2 and PILOT-50/51 ones still in progress, plus REQ-GATE-01..03 |
| FAILED | 0 | |
| SELF-ASSERTED | 3 | REQ-GATE-01..03: the CSV says PASS and nothing machine-readable backs it |
| UNPROVEN | 0 | |
| UNVERIFIED-RESULT | 17 | The REQ-CLI and REQ-V2C/X/O IDs tagged in the harness |
| ORPHANED | 0 | Was 2 in v1. Fixtures moved to `cli/tests/fixtures/`, which `.evidenceignore` excludes |
| UNTRACED | 10 | |
| DUPLICATE-ID | 1 | REQ-EVAL-01, which the lead is renaming under REQ-V2C-09 |

With the harness's own results ingested
(`JUNIT_OUT=… bash cli/tests/test_cli_fixtures.sh`, then `gaps --results …`),
**17 requirements are PROVEN** and UNVERIFIED-RESULT drops to 0:
- REQ-CLI-01..07
- REQ-V2C-02, -03, -04, -05, -06, -08, -10
- REQ-V2O-03, -04
- REQ-V2X-02

Commenting a requirement ID next to a test no longer counts as coverage. So
REQ-CLI-01..03 are covered only because the harness labels now carry the IDs as
test titles.
