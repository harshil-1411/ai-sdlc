# evidence

A small, dependency-free CLI that derives the traceability chain (tracker key,
requirement, test, test result, commit, approval, agent session) from what a
repository has actually committed and actually run. Nothing is assembled by hand
at release time. It is the instrument that tests whether "evidence can be derived
rather than assembled" is true here.

## Install

Nothing to install. `cli/evidence` is a single Python 3 script that uses only the
standard library. It makes no network calls unless you opt in: `tracker ...` and
`export --github` call the GitHub CLI (`gh`).

```
python3 cli/evidence doctor
```

## Commands

| Command | What it does | Exit codes |
| --- | --- | --- |
| `doctor [--strict]` | Preflight checks for the gate environment | 0 = no FAIL; 1 = a FAIL (or any WARN with `--strict`) |
| `scan [--repos A,B\|DIR] [--results P]` | Builds and prints the graph | 0 |
| `gaps [--strict] [--repos A,B\|DIR] [--parent KEY] [--results P] [--only-results] [--self-check]` | Reports gap categories | 0 = no blocking gap; 1 = blocking gap; 2 = nothing to assess |
| `export [--format csv\|md] [--write] [--conflicts-only] [--github] [--results P]` | Merges the matrix | 0; `--conflicts-only` exits 1 while any conflict exists |
| `tracker check <KEY>` / `tracker link <KEY> <url-or-text>` | GitHub Issues through `gh` | 0 = ok; 1 = not found or write failed; 2 = not configured |

`--results PATH` can be repeated. It adds a JUnit XML file, a `claude plugin eval`
`aggregate-result.json`, or a directory of either, to the results named by
`test_results_location`.

`gaps --only-results` (2.3.0) reads **only** the `--results` paths and ignores the
adapter's `test_results_location`, so a stale or committed result can't prove anything.
Without `--results` it exits 2 before reading anything. CI's `sign-and-gate` job uses it on
the freshly downloaded artifact (ADR-0002).

`gaps --self-check` (2.3.0) is for this repository's own `scripts/ci/run-tests.sh`, whose
last step runs `gaps --strict --self-check --only-results --results "$out"`. It exempts
exactly one requirement, `REQ-V2C-09` (`SELF_CHECK_REQUIREMENT`, hard-coded in the CLI),
because that run is its proof, and it says so in the output. No adapter key can name or change
the exempt ID. The authoritative `gaps --strict` in CI runs without it.

After a local `bash scripts/ci/run-tests.sh`, pass the directory it printed:
`evidence gaps --strict --results <dir>`. Test results are CI artifacts; nobody commits them.

### `evidence doctor`

| Check | Status when it fails |
| --- | --- |
| `python3` on PATH | FAIL |
| `jq` on PATH | FAIL if any `plugins/*/scripts/*.sh` calls `jq`, otherwise WARN |
| every `plugins/*/scripts/*.sh` readable | FAIL |
| every `hooks.json` parses and every script it references exists | FAIL |
| `.evidence/context/` exists | FAIL |
| every known profile present (`stack`, `deployment`, `toolchain`, `design-system`, `compliance`) | WARN, listing the missing ones |
| `validation/traceability.csv` header names `requirement_id` | FAIL (the file would otherwise be read as zero rows) |
| unresolved `[ASK]` count > 0 | WARN, with a count per file |
| profile older than about 6 months | WARN |
| a control set in the `## Applicable frameworks` table of `compliance.md` still says `Owner: UNASSIGNED` | WARN, naming the sets. It checks `references/*.md` under `regulatory-controls` (not `README.md`/`SKILL.md`) in this repo, next to the CLI, or in `$EVIDENCE_CONTROLS_DIR` |
| `test_results_location` in the adapter resolves | WARN |
| `.evidenceignore` uses `!` negation | WARN (not supported) |

`doctor` also runs a **live gate canary**: it feeds the shipped engine an unapproved
source write and a docs write in a throwaway repository and FAILs unless the first is
denied and the second allowed.

### `evidence gaps` — the category set

A requirement is **covered** when a test carries a *structural* tag for it (see
below), or when a `validation/traceability.csv` row names both the requirement and
a `test_case_id` that appears in the `automated_test` file it cites (the legacy,
manual path). A requirement is **PROVEN** only when a covering test shows up as
**passed** in an ingested, machine-readable result. A hand-typed `PASS` in the CSV
never proves anything.

| Category | Meaning | Blocks by default | Blocks with `--strict` |
| --- | --- | --- | --- |
| `PROVEN` (listed first, informational) | Covered, and the latest ingested result of a covering test passed | — | — |
| `NO COVERAGE` | No structural tag, and no corroborated CSV claim | yes | yes |
| `FAILED` | The latest ingested result of a covering test failed or errored | yes | yes |
| `MISSING-CHILD` | With `gaps --repos A,B`: a participating repo has no `PARENT/CHILD` commit chain for a parent key seen in another participant | yes | yes |
| `SELF-ASSERTED` | The CSV `result` starts with `PASS`, but no ingested result corroborates it | no | yes |
| `UNPROVEN` | The CSV `result` is empty or not `PASS`, and there is no ingested pass | no | yes |
| `UNVERIFIED-RESULT` | Covered, but there is no result of any kind (no ingested result and no CSV `result`) | no | yes |
| `ORPHANED` | A structural tag names a requirement ID that no spec defines | no | no |
| `UNTRACED` | A commit carries no tracker key | no | no |
| `DUPLICATE-ID` | A requirement ID is defined more than once (the first definition is kept). Specs are read before plans; a plan row (a `spec_glob` file that also matches `artifact_chain.plan_glob`) repeating an ID its `From:` spec (or that spec's directory) defines is a **reference**, not a definition (2.3.0). A plan-only ID (Tier 1) is still defined by its plan | no | yes |

Each requirement lands in at most one of `PROVEN` / `FAILED` / `SELF-ASSERTED` /
`UNPROVEN` / `UNVERIFIED-RESULT`. `--strict` therefore means **every requirement
is PROVEN**. When there is more than one ingested run of the same test, the latest
wins (JUnit `testsuite@timestamp`, else the file's mtime; eval `startedAt`).

Every run prints an `Assessment basis:` line. It gives the counts of
requirements, tests, unreadable files and ingested results, names the
`.evidenceignore` patterns, and warns when a results location is missing. It also
warns when the CSV header is malformed. A malformed CSV is never parsed into
fabricated rows, and `export --write` refuses to write over one.

### Structural tags (what counts as coverage)

| Form | Example |
| --- | --- |
| decorator / marker / annotation carrying the ID | `@pytest.mark.req("REQ-X-01")`, `@req("REQ-X-01")`, `@Tag("REQ-X-01")` |
| test-framework title carrying the ID | `it("REQ-X-01: rejects ...")`, `test('... REQ-X-01 ...')`, `describe(...)`, bats `@test "REQ-X-01 ..."`, shell harness `check_* "REQ-X-01: ..."` |
| Playwright tag option | `test('checkout', { tag: ['@REQ-X-01'] }, ...)` |
| declared test name containing the ID token | `def test_REQ_X_01_rejects_bad_password` |
| Gherkin tag line | `@REQ-X-01` above a `Scenario:` |
| eval case frontmatter | `covers: [REQ-X-01]` in `plugins/*/evals/<case>/prompt.md` (the adapter's `eval_glob` overrides the path) |

None of these count: a comment (`# REQ-X-01`, `// covers REQ-X-01`), a
commented-out test call, a docstring paragraph, prose in an eval prompt, or the ID
appearing anywhere else in a test-shaped file. Each tag is bound to the test it
decorates or names. That binding is how an ingested result is matched to a
requirement: the result's name must match the bound test, and its `file` or
dotted `classname` must match the test's file. A result whose testcase name or
`<property>` carries the ID also matches, as long as the requirement is covered in
this repo.

The following paths are treated as tests: any path segment in `test_dir_segments`
(default `tests`, `__tests__`, `qa`), basenames `test_*`, `*_test.*`, `*.test.*`,
`*.spec.*`, `*_spec.*`, `*Test.java|kt|scala|cs`, `*.feature`, `*.bats`, and eval
cases. `.git`, `node_modules`, `__pycache__`, `.venv`, `venv` and `.tox` are never
walked.

### `.evidenceignore`

This is a file at the repo root with gitignore-style globs, kept deliberately
simple:

- Blank lines and lines starting with `#` are skipped.
- A pattern that contains `/` is anchored to the root. A pattern without one
  matches at any depth.
- A trailing `/` matches directories only.
- `*` does not cross `/`. `**` does.
- `!` negation is **not** supported, and `doctor` warns when it is used.

Ignored paths are excluded from both test and spec scanning. This repo ignores
`cli/tests/fixtures/`, because those files tag made-up `REQ-FIX-*` IDs on purpose.

### Results ingestion

- **JUnit XML** (pytest `--junitxml`, Jest `jest-junit`, Maven Surefire,
  Playwright `junit` reporter, and so on). `<failure>` or `<error>` means failed,
  `<skipped>` means skipped (neither a pass nor a fail), and anything else means
  passed. Files that contain `<!DOCTYPE`/`<!ENTITY` are refused and counted as
  unparseable.
- **`claude plugin eval` `aggregate-result.json`** (`schemaVersion: 1`). A case
  passes when `aggregates.passRate >= suite.threshold`. A case whose every `with`
  run ended in an infrastructure `error` is treated as skipped. The case is
  matched to `<suite.root relative to the repo>/<case.dir>`, or to
  `plugins/<basename of suite.root>/<case.dir>` when the suite root is elsewhere.
- **Where results come from:** `test_results_location` in `.evidence/adapter.yml`
  (a path, a directory, a glob, or a list; `none` disables it), plus every
  `--results`. With no adapter at all, the default is `plugins/*/evals/results`.

### `evidence export`: merge, never rewrite

The columns are the template's columns plus `approved_by` and `agent_sessions`.
Any extra columns already in the CSV are kept.

- A non-empty existing cell is **never overwritten**. That includes
  `evidence_link`, `result`, `requirement_summary` and `test_run_id`. If the
  derived value differs, the difference is reported as a **conflict**: on stdout
  with `--write`, on stderr otherwise, and alone with `--conflicts-only`.
- Empty cells are filled with derived values.
- The list columns (`automated_test`, `implementing_commits`, `agent_sessions`,
  `approved_by`) gain new items. Items already there are never removed.
- Rows for new requirements are appended. **No row is ever deleted**, including
  rows no spec mentions any more.

Derived columns:

| Column | Source |
| --- | --- |
| `implementing_commits` | Commits whose message carries the requirement's tracker key, or a `PARENT/CHILD` pair containing it, excluding the spec commit |
| `agent_sessions` | `Agent-Session:` / `Claude-Session:` trailers of those commits |
| `approved_by` | `.evidence/changes/<KEY>/approval.json` (`{"key","plan_path","plan_sha256","approver","method","approved_at"}`). This shows as `approver (method, approved_at)`, and gets `[STALE: plan changed since approval]` appended when the plan's sha256 no longer matches. With `--github`, it also adds `github:<login> (PR #n)` for each `APPROVED` review on PRs whose title contains the key (`gh pr list --search <KEY> --state all --json number,title,reviews`) |
| `result` / `test_run_id` / `evidence_link` | The ingested results for a PROVEN or FAILED requirement, for example `PASS (ingested: 1 result(s))`, `pytest@2026-09-24T10:00:00`, and the results file path |

The tracker key is taken from the spec's introducing commit. If that commit has
no key, it falls back to the spec's `Tracker:` line.

### `evidence tracker` (GitHub Issues)

```
# .evidence/adapter.yml
tracker: github
tracker_key_to_issue: GH-(\d+)     # first capture group is the issue number
```

`tracker check GH-42` runs `gh issue view 42 --json number,title,state,url`.
`tracker link GH-42 <url-or-text>` runs `gh issue comment 42 --body "Evidence link (GH-42): <url-or-text>"`.
Set `EVIDENCE_GH=/path/to/executable` to replace `gh`. The tests use this to run a
fake `gh`.

**Jira** is not implemented. Use this REST template, where the key is the Jira
issue key:

```
# check
curl -sf -u "$JIRA_USER:$JIRA_API_TOKEN" \
  "https://$JIRA_HOST/rest/api/3/issue/$KEY?fields=summary,status"
# link (remote link; idempotent per globalId)
curl -sf -u "$JIRA_USER:$JIRA_API_TOKEN" -X POST -H 'Content-Type: application/json' \
  "https://$JIRA_HOST/rest/api/3/issue/$KEY/remotelink" \
  -d "{\"globalId\":\"evidence:$URL\",\"object\":{\"url\":\"$URL\",\"title\":\"Evidence ($KEY)\"}}"
```

### Multi-repo: `--repos`

- `--repos A,B,C` lists the **participating** repositories explicitly. `gaps`
  reports each repo's categories, plus `CROSS-REPO COVERAGE GAPS` (a requirement
  covered in some repos but not others, which blocks) and `MISSING-CHILD`: every
  parent key seen in a `PARENT/CHILD` pair must have a child chain in every listed
  repo. Use `--parent KEY` to check one parent only.
- `--repos DIR` walks the sibling git repos under `DIR`. That tells you nothing
  about which repos participate, so `MISSING-CHILD` is not assessed in this mode.

### Adapter (`.evidence/adapter.yml`)

The adapter is a flat `key: value` file. It supports indented `- item` lists,
inline `[a, b]` lists, one level of nested mapping (`artifact_chain:` with `plan_glob:`), and quoted
values. **Comments (2.3.0):** a `#` at the start of a value or after whitespace, outside single or
double quotes, starts a YAML comment and ends the value, for scalars, `- item` entries and inline
lists alike (`- intent/*/spec.md   # specs` is the glob `intent/*/spec.md`). A `#` inside quotes
(`'REQ-#-[0-9]+'`) or with no whitespace before it (`a#b`) is part of the value. Eval `covers:`
lines follow the same rule. Keys: `requirements_source`,
`spec_glob`, `requirement_pattern`, `tracker_pattern`, `test_dir_segments`,
`eval_glob`, `test_results_location`, `tracker`, `tracker_key_to_issue`. See
`.evidence/adapter.example.yml`.

## Testing the CLI itself

```
bash cli/tests/test_cli_fixtures.sh
JUNIT_OUT=/tmp/cli-fixtures.xml bash cli/tests/test_cli_fixtures.sh   # also write JUnit
python3 cli/evidence gaps --results /tmp/cli-fixtures.xml              # dogfood: PROVEN
```

The harness builds throwaway git repos and asserts on exit codes, output and files
on disk. It covers:

- **Fixtures 1–9:** exit 0/1/2, structural versus loose matches, CSV
  corroboration, UNVERIFIED-RESULT and SELF-ASSERTED, a malformed CSV, and
  DUPLICATE-ID.
- **Fixture 10:** every structural form, and every non-structural one.
- **Fixture 11:** `.evidenceignore`.
- **Fixture 12:** JUnit PASS/FAIL, latest-wins, `--strict`, the adapter
  `test_results_location`, and DOCTYPE refusal.
- **Fixture 13:** eval `covers:` plus `aggregate-result.json`.
- **Fixture 14:** adapter overrides.
- **Fixture 15:** doctor WARN/FAIL/`--strict`, owner placeholders, and exec-form `bash -c` hooks.
- **Fixture 16:** export merge, conflicts, `--conflicts-only`, and no deletion.
- **Fixture 17:** `approved_by` (local, stale, and `--github`), `agent_sessions`,
  and `implementing_commits`.
- **Fixture 18:** `tracker check`/`link` through a mocked `gh`.
- **Fixture 19:** `--repos A,B` MISSING-CHILD, and `scan --repos DIR`.

Each check's label starts with the requirement IDs it proves, so the harness's
JUnit output PROVES this repo's `REQ-CLI-*` / `REQ-V2C-*` requirements.

## What this does not do

- It does not parse test code. The structural forms above are recognised
  line by line. A framework with a different tagging syntax needs a new form
  here, and until then its tags don't count, so the CLI errs toward NO
  COVERAGE.
- It does not call Jira or any other tracker except GitHub Issues through `gh`.
- It does not cryptographically verify approvals. A local `approval.json` is only
  as trustworthy as the control that stops the agent from writing it (the
  engine's control-plane protection). `--github` reviews are bound to an
  identity.
- It does not ingest TestRail/Xray or other test-management exports. Convert
  them to JUnit XML first.
