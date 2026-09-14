# Review brief: the evidence CLI

This document exists because `cli/evidence` was written in one session with no human
reviewer, and it is the artifact that will be shown to external compliance people. It
gets the review this framework prescribes for everything else. This brief prepares
that review — it does not perform it. If you are the reviewer, start at the checklist
(section e), not the top.

## a) Structure walkthrough

The whole tool is one file, `cli/evidence` (~825 lines), because the four subcommands
share almost everything and the ~800-line scope-discipline ceiling this framework sets
for itself argued against splitting into a package prematurely. It has grown past that
ceiling by the item-1 correctness fix; see section (c).

**Layout, top to bottom:**

1. **Constants** (`CSV_COLUMNS`, `DEFAULT_TRACKER_PATTERN`, `DEFAULT_REQ_PATTERN`,
   `DEFAULT_TEST_DIR_SEGMENTS`, `DEFAULT_TEST_BASENAME_PATTERNS`, `TEST_DECL_RE`,
   `TEST_TAG_RE`, `STALE_DAYS`, `KNOWN_PROFILES`). Every regex a reviewer needs to
   judge is declared here, not buried inline.

2. **Small helpers** — `find_repo_root` (walk up to the nearest `.git`), `run_git`
   (subprocess wrapper, swallows failure to `None`), `is_git_repo`, `read_text`
   (returns `None`, not `""`, on any read failure — this distinction matters, see
   section b), `iter_files`, `find_structural_req_ids` (the coverage-matching heuristic
   from the item-1 fix — see section (e), read this one first).

3. **Adapter reader** (`load_adapter`, `adapter_get`) — a deliberately minimal
   `key: value` / `key:` + `- item`-list parser for `.evidence/adapter.yml`. Not a YAML
   parser; will silently misparse anything outside that subset (nested maps, multi-line
   strings, quoted scalars with colons in them). See section (b).

4. **`cmd_doctor`** — six independent checks (jq on PATH, gate-script readability,
   hooks.json validity + referenced-script existence, `.evidence/context/` presence,
   `[ASK]` count, profile staleness), each tagged PASS/FAIL/WARN, critical ones
   determining the exit code.

5. **`build_graph`** — the one function `scan`, `gaps` and `export` all call. Reads:
   - **Requirements**: `intent/*/spec.md` (or `adapter`'s `spec_glob`), one entry per
     markdown-table row whose ID matches `requirement_pattern`. `spec_commit` is the
     *oldest* commit touching that file (`git log --follow`, last line) — an
     approximation of "when this requirement was introduced," not a guarantee (see
     section b).
   - **Tests**: any file under a recognised test directory or basename, with
     `find_structural_req_ids` extracting only IDs structurally tied to a test
     declaration or tag (the item-1 fix).
   - **Commits**: full `git log`, each tagged with whatever tracker keys
     `tracker_pattern` finds in the subject+body.
   - **Traceability rows**: `validation/traceability.csv` if present, read as-is.
   Also tracks `skipped_files` (unreadable files, never silently treated as empty) and
   two description strings used in the `Assessment basis:` line.

6. **`cmd_scan`** — prints the graph. Handles `--repos <dir>` (walks sibling
   repositories, reports which tracker-key *parents* — see `traceability-ids`'
   `PARENT/CHILD` convention — join more than one repo) as a separate code path from
   the single-repo case.

7. **`csv_row_corroborated`** (item-1 fix) — the function that decides whether a
   `validation/traceability.csv` row's claim is trusted. Read this before trusting any
   `gaps`/`export` output. See section (e).

8. **`compute_gaps`** — builds the four categories from the graph plus the
   corroboration check. `NO COVERAGE` entries for a requirement with an uncorroborated
   CSV claim carry the specific reason inline, not just the bare ID.

9. **`cmd_gaps`** — the "nothing to assess" (exit 2) check happens *before* calling
   `compute_gaps`, as a genuinely separate code path, not a post-hoc reinterpretation
   of an empty gaps result. `--repos` mode computes per-repo gaps and then a
   cross-repo comparison keyed on the parent tracker key.

10. **`cmd_export`** — re-reads the existing CSV (if any), upserts a row per
    currently-discovered requirement (preserving rows for anything not touched this
    scan — the append-safety guarantee), and writes CSV or Markdown. The
    `Assessment basis:` line for CSV format goes to **stderr**, specifically so
    `evidence export --format csv > file.csv` still redirects clean, re-parseable CSV
    (an early draft put it in the CSV body as a `#`-comment; that would have made the
    file's own header the *second* line and broken every future re-read — caught before
    shipping, not after).

**Data flow, scan through export:** `build_graph` is the single source of truth;
`scan` prints it, `compute_gaps` (used by `gaps`) analyzes it, `cmd_export` re-derives
CSV rows from it while merging against whatever CSV already exists on disk. Nothing
computed in `gaps` is recomputed differently in `export` — both call the same
`csv_row_corroborated` for the same question.

## b) Assumptions a reviewer should check

- **Requirement ID recognition**: a line in a markdown table cell matching
  `REQ-[A-Za-z0-9]+-[0-9]+` (or the adapter's override). Assumes the framework's own
  `REQ-<area>-<nn>` convention; a repository using a different shape (`JIRA-REQ-123`,
  bare `US-4021`) gets zero requirements found unless `.evidence/adapter.yml` overrides
  `requirement_pattern`. Not auto-detected.
- **Test-to-requirement matching** (the item-1 fix): a requirement ID counts as
  structurally linked to a test only if a recognised test-declaration keyword
  (`def test_`, `it(`, `describe(`, `class Test*`, `function test*`, `@Test`) or an
  explicit tag (`@covers`, `# covers`, `@requirement`, `@pytest.mark`) appears within
  one line above or below the ID. This is a **heuristic across languages**, not a real
  parser for any one test framework. It will miss frameworks that declare tests
  differently (RSpec's `context`/`example`, Go's `func Test...(t *testing.T)` — this
  one is actually NOT matched, since the regex requires `def`/`function`/`class
  Test`/`it(`/`describe(`/`@Test` and Go's bare `func TestFoo(` matches none of them).
  **This is a real gap, not a hypothetical one — flagging it here rather than
  discovering it only when someone runs this against a Go repository.**
- **Commit attribution**: a commit "carries a tracker key" if `tracker_pattern` matches
  anywhere in its subject or body — no check that the key names a real, existing issue
  (the CLI has no network access to verify against a tracker). A fabricated or
  copy-pasted-wrong key would pass this check.
- **Adapter missing-field behaviour**: every `adapter_get` call has a hardcoded default
  and silently falls back to it if the adapter file doesn't set that key — there is no
  "adapter is present but incomplete" warning distinct from "adapter absent entirely."
  A reviewer relying on the adapter to *override* a default should verify the key name
  is spelled exactly as `load_adapter`'s minimal parser expects (flat `key: value`,
  no nested structure).
- **Malformed input**: `hooks.json` with invalid JSON is caught and reported by
  `doctor` (a `try/except json.JSONDecodeError`). A malformed `.evidence/adapter.yml`
  (anything outside the flat-key/list subset) is NOT caught explicitly — it silently
  parses into whatever the line-based reader happens to produce, which may be wrong
  without erroring. **A malformed `validation/traceability.csv` (wrong column names,
  no header at all) is now caught explicitly** (`csv_header_ok`, checked in
  `build_graph`, `cmd_doctor`, and `cmd_export`'s own re-read): this used to be a
  live bug, not a hypothetical one — `csv.DictReader` silently returns `None` for a
  missing column, which meant a completely garbage CSV produced a fabricated
  `requirement_id="?"` finding indistinguishable from a real one. Found by direct
  reproduction, fixed by refusing to parse rows from a header that doesn't contain
  `requirement_id`, surfacing a loud warning (and a critical `doctor` failure)
  instead, and having `export --write` refuse to run against it rather than risk
  silently overwriting whatever it held.
- **Duplicate requirement IDs**: a requirement ID reused across two `spec.md` files,
  or repeated within one, used to be silently dropped after the first occurrence —
  also a live bug, also found by direct reproduction. Now tracked via
  `req_id_occurrences` in `build_graph` and surfaced as its own `DUPLICATE-ID` gap
  category. The first occurrence is still the one kept as canonical (unchanged);
  what changed is that the collision is now reported instead of silently erased.

## c) Where I am least confident

Named honestly, in descending order of how much I'd want a second opinion:

1. **The structural-matching heuristic (`find_structural_req_ids`, `TEST_DECL_RE`,
   `TEST_TAG_RE`)** is the highest-consequence piece of code in the tool — it is
   literally what item-1's bug was about — and it is also the piece with the least
   principled basis. I chose a ±1-line window and a specific list of keywords because
   they covered the fixtures I could think to write, not because I derived them from a
   survey of real test suites. A different reasonable implementation might: require the
   tag on the *same* line only (stricter, fewer false positives, more false negatives);
   use a wider window (looser); or require the ID to appear inside an actual parsed
   AST node for known languages (much stronger, much more work, and language-specific
   in a framework that otherwise never hardcodes anything about a stack). I'd genuinely
   like someone to argue for a different point on that spectrum.
2. **`spec_commit` as "the oldest commit touching this file"** (`git log --follow`,
   last line) is a guess at "when was this requirement introduced," not a guarantee.
   A spec file that was renamed, split, or had requirements added long after creation
   would report a `spec_commit` that doesn't actually correspond to when *that specific
   requirement ID* was introduced. I did not implement per-requirement blame (e.g.
   `git log -S<req_id>`) because it's meaningfully slower for large histories and I
   judged the approximation acceptable for a Tier 1 tool — but that's a judgement call,
   not a proof.
3. **The CSV-corroboration check (`csv_row_corroborated`) treats "the ID appears
   anywhere in the named file's raw text" as sufficient corroboration.** This is
   deliberately weaker than the structural test-matching check (which requires
   line-adjacency to a declaration/tag) — I judged that a human explicitly wrote this
   CSV row citing this specific file, so requiring only "the string is somewhere in
   there" is a reasonable minimum bar, not the same bar as inferring linkage from
   scratch. A stricter reviewer might reasonably argue this should require the *same*
   structural adjacency check used for test files, not mere presence.
4. **The `--repos` cross-repo join key** (`parent_key`, splitting `PARENT/CHILD` on
   `/` and taking the first half) assumes every repository in a cross-repo change
   consistently writes the key as `PARENT/CHILD` in that exact order with a literal
   `/`. Nothing enforces this; a repository that only ever wrote the child key alone
   would never join.
5. **The `TEST_DECL_RE`/`TEST_TAG_RE` regexes are English-keyword-based** (`covers`,
   `requirement`, `req:`) — a codebase that tags in another language, or with a
   house convention like `# proves` or `# validates`, gets zero matches from this
   default and needs `.evidence/adapter.yml`'s (currently unimplemented —- see section
   d) `test_tag_pattern` field to override it.
6. **`UNVERIFIED-RESULT` (the item-3 fix) knows about exactly one way a result can be
   recorded: a non-empty `result` field on a `validation/traceability.csv` row for
   that requirement.** It cannot see a CI test report, a JUnit XML file, or any other
   place a real pass/fail outcome might actually live — a requirement whose test runs
   green in CI every commit but has no corresponding CSV row shows up here
   indistinguishable from one that has genuinely never been run. This is a deliberate,
   narrow claim: "nobody recorded a result in the one place this tool can check," not
   "this test has never passed." Overclaiming the second from the first would be
   exactly the kind of confident-wrong assurance this tool exists to avoid producing.
   It is also, by design, informational only — it does not affect `gaps`' exit code,
   the same way `UNPROVEN` does not; only `NO COVERAGE` blocks.

## d) What is NOT covered by the CLI's own tests

- **`doctor`'s six checks** — all verified manually in this session (jq missing,
  hooks.json referencing a deleted script, missing `.evidence/context/`), pasted into
  the session transcript and the `ITEM-1` commit message, but never captured as a
  committed, repeatable fixture. `test_cli_fixtures.sh` has no `doctor` case.
- **Adapter override behaviour** (`requirements_source: tracker`, custom
  `tracker_pattern`/`requirement_pattern`/`spec_glob`) — verified manually against a
  synthetic repository in this session, not automated.
- **`export`'s append-safety guarantee** — verified manually (ran `export --write`
  twice, confirmed no duplication), not automated.
- **`--repos` cross-repo rollup** (`scan --repos`, `gaps --repos`) — verified manually
  against a synthetic two-repository scenario, not automated.
- **The adapter file's parser itself** (`load_adapter`) has no test at all, automated
  or manual-and-documented, beyond it working correctly for the one adapter file
  actually written in this repository (`.evidence/adapter.example.yml`, which is
  entirely commented out as documentation, not a live adapter).
- **Malformed-CSV handling**: previously true (`csv.DictReader`'s actual behaviour
  on a missing/wrong header was never exercised deliberately) — no longer accurate.
  `csv_header_ok` is now exercised by fixtures 8 and 9 in
  `cli/tests/test_cli_fixtures.sh` (malformed header must warn and must not
  fabricate a finding; `export --write` must refuse to run against it). A CSV with
  a merely **reordered** header (same columns, different order) was never broken —
  `DictReader` is column-name-based, not positional — so that half of this item's
  original phrasing was imprecise; only a header missing `requirement_id` entirely
  is treated as malformed.

REQ-CLI-04 through REQ-CLI-07 in `intent/2026-09-12-evidence-cli/spec.md` name exactly
these gaps and are marked `[NEEDS VERIFICATION — manual only]` in that spec's proof
table, matching this list one-for-one.

## e) Reviewer checklist, ordered by consequence

1. **`find_structural_req_ids` and the `TEST_DECL_RE`/`TEST_TAG_RE` patterns** (top of
   the file). This is what item-1 fixed and what section (c)#1 names as the least
   principled piece of code here. If this is wrong, every other number the tool
   reports is wrong downstream of it.
2. **`csv_row_corroborated`**. The second half of the item-1 fix. Check whether "the
   ID appears anywhere in the file" is the right bar, per section (c)#3.
3. **The three `gaps` exit codes and the `all_known_reqs` check that decides between
   exit 2 and the rest** (`cmd_gaps`, single-repo branch). Confirm a repository with
   real evidence only in `validation/traceability.csv` (no spec.md at all) is not
   wrongly routed to exit 2 "nothing to assess."
4. **`assessment_basis_line`** — confirm the counts it reports actually match what a
   reviewer can independently verify by re-running `scan` themselves; a basis line
   that itself can't be trusted defeats its purpose.
5. **`csv.DictReader` usage in `build_graph` and `cmd_export`** — what happens on a
   `validation/traceability.csv` with a malformed header (see section d). Not tested;
   worth a deliberate try before this is relied on for a real release gate.
6. **`load_adapter`'s minimal YAML subset** — confirm it fails loudly (or at least
   visibly) rather than silently on a `.evidence/adapter.yml` written outside the
   flat-key/list shape it expects.
7. **The `--repos` parent-key join** (section c#4) — low consequence today (no
   repository actually uses this in production yet) but worth a second opinion before
   it is relied on for a real cross-repo audit.

## Known dogfood result

Running `evidence scan` / `evidence gaps` against this repository, after retrofitting
`intent/2026-09-12-evidence-cli/{intent,spec}.md` (see the commit that added this
file): 10 requirements found (7 `REQ-CLI-*`, 3 `REQ-GATE-*`), 7 report `NO COVERAGE` —
`REQ-CLI-04` through `-07` (no automated fixture yet, exactly as this brief's section d
says) and all three `REQ-GATE-*` (the pre-existing, honestly-reported item-1 finding
that `gate-regression-tests.sh` doesn't literally contain the case IDs its own
`validation/traceability.csv` row claims). Exit 1. This is the correct, current, honest
state of this repository's own traceability — not a defect in this brief or in the
CLI's dogfood run.
