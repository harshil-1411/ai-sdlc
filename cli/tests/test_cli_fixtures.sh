#!/bin/bash
# Regression fixtures for cli/evidence. Each check's label starts with the
# requirement ID(s) it proves (REQ-CLI-* from intent/2026-09-12-evidence-cli,
# REQ-V2C-* / REQ-V2X-* / REQ-V2O-* from intent/2026-09-24-v2-enterprise-hardening).
# That label is the structural tag `evidence gaps` reads, and the JUnit testcase
# name when JUNIT_OUT is set:
#
#   JUNIT_OUT=validation/results/cli-fixtures.xml bash cli/tests/test_cli_fixtures.sh
#
# Tagged test files, JUnit/eval results and the fake `gh` used below live in
# cli/tests/fixtures/ (excluded from this repo's own scan by .evidenceignore,
# because they tag made-up REQ-FIX-* IDs on purpose). Spec tables are written
# inline with heredocs; a spec table row is not a test tag.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI="$(cd "$HERE/.." && pwd)/evidence"
FIX="$HERE/fixtures"
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

pass=0
fail=0
JUNIT_CASES=""

xml_escape() { printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' -e 's/"/\&quot;/g'; }

record() {  # record <label> <ok:0|1> [detail]
  local label="$1" ok="$2" detail="${3:-}"
  if [ "$ok" = 0 ]; then
    pass=$((pass + 1))
    JUNIT_CASES+="    <testcase classname=\"cli.tests.test_cli_fixtures\" name=\"$(xml_escape "$label")\"/>"$'\n'
  else
    fail=$((fail + 1))
    JUNIT_CASES+="    <testcase classname=\"cli.tests.test_cli_fixtures\" name=\"$(xml_escape "$label")\"><failure message=\"check failed\">$(xml_escape "$detail")</failure></testcase>"$'\n'
  fi
}

make_repo() {
  local dir="$1"
  mkdir -p "$dir"
  git -C "$dir" init -q -b main
  git -C "$dir" -c user.email=t@t.com -c user.name=t commit -q --allow-empty -m init
}

commit_all() {  # commit_all <dir> <message...>
  local dir="$1"; shift
  git -C "$dir" add -A
  git -C "$dir" -c user.email=t@t.com -c user.name=t commit -q "$@"
}

write_spec() {  # write_spec <dir> <tracker> <req-id> <summary> [more "id|summary" ...]
  local dir="$1" key="$2"; shift 2
  mkdir -p "$dir/intent/2026-01-01-demo"
  {
    echo "# Spec: Demo"
    echo "Tracker: $key"
    echo
    echo "## Requirements"
    echo "| ID | Requirement | Source | Acceptance |"
    echo "| --- | --- | --- | --- |"
    while [ $# -gt 0 ]; do
      echo "| $1 | $2 | intent.md | it works |"
      shift 2
    done
  } > "$dir/intent/2026-01-01-demo/spec.md"
}

run_cli() {  # run_cli <dir> <args...> -> sets OUT, STATUS
  OUT=$(cd "$1" && shift && python3 "$CLI" "$@" 2>&1)
  STATUS=$?
}

check_exit() {
  local label="$1" dir="$2" cmd="$3" expected="$4"
  # shellcheck disable=SC2086
  run_cli "$dir" $cmd
  if [ "$STATUS" = "$expected" ]; then
    record "$label" 0; echo "PASS: $label (exit $STATUS)"
  else
    record "$label" 1 "expected exit $expected, got $STATUS"
    echo "FAIL: $label (expected exit $expected, got $STATUS) -- output:"
    echo "$OUT" | sed 's/^/    /'
  fi
}

check_contains() {
  local label="$1" dir="$2" cmd="$3" needle="$4"
  # shellcheck disable=SC2086
  run_cli "$dir" $cmd
  if echo "$OUT" | grep -qF -- "$needle"; then
    record "$label" 0; echo "PASS: $label"
  else
    record "$label" 1 "expected to find: $needle"
    echo "FAIL: $label -- expected to find: $needle"
    echo "$OUT" | sed 's/^/    /'
  fi
}

check_not_contains() {
  local label="$1" dir="$2" cmd="$3" needle="$4"
  # shellcheck disable=SC2086
  run_cli "$dir" $cmd
  if echo "$OUT" | grep -qF -- "$needle"; then
    record "$label" 1 "expected NOT to find: $needle"
    echo "FAIL: $label -- expected NOT to find: $needle"
    echo "$OUT" | sed 's/^/    /'
  else
    record "$label" 0; echo "PASS: $label"
  fi
}

check_file() {  # check_file <label> <file> <grep -F needle> [absent]
  local label="$1" file="$2" needle="$3" mode="${4:-present}"
  local found=1
  grep -qF -- "$needle" "$file" 2>/dev/null && found=0
  if { [ "$mode" = present ] && [ $found = 0 ]; } || { [ "$mode" = absent ] && [ $found = 1 ]; }; then
    record "$label" 0; echo "PASS: $label"
  else
    record "$label" 1 "$needle should be $mode in $file"
    echo "FAIL: $label -- '$needle' should be $mode in $file:"
    sed 's/^/    /' "$file" 2>/dev/null
  fi
}

# ---- Fixture 1: requirements, no tests at all -> all uncovered, exit 1 ----
F1="$SCRATCH/f1_no_tests"
make_repo "$F1"
write_spec "$F1" FIX-1 REQ-FIX-01 "Something with no test anywhere"
commit_all "$F1" -m "FIX-1: add spec, no tests"
check_exit "REQ-CLI-01: Fixture 1: requirement with no test -> exit 1" "$F1" "gaps" 1
check_contains "REQ-CLI-01: Fixture 1: the requirement is listed as NO COVERAGE" "$F1" "gaps" "REQ-FIX-01"

# ---- Fixture 2: no requirements anywhere -> exit 2 ----
F2="$SCRATCH/f2_empty"
make_repo "$F2"
echo "hello" > "$F2/README.md"
commit_all "$F2" -m "init readme"
check_exit "REQ-CLI-01: Fixture 2: no requirements anywhere -> exit 2" "$F2" "gaps" 2
check_contains "REQ-CLI-01: Fixture 2: says nothing to assess" "$F2" "gaps" "Nothing to assess"

# ---- Fixture 3: a requirement with a structurally tagged test -> exit 0 ----
F3="$SCRATCH/f3_covered"
make_repo "$F3"
write_spec "$F3" FIX-1 REQ-FIX-02 "Something with a real, tagged test"
mkdir -p "$F3/tests" && cp "$FIX/tagged/test_demo_fix02.py" "$F3/tests/"
commit_all "$F3" -m "FIX-1: add spec and a real tagged test"
check_exit "REQ-CLI-02 REQ-V2C-04: Fixture 3: marker-tagged test -> exit 0" "$F3" "gaps" 0
check_contains "REQ-CLI-02 REQ-V2C-04: Fixture 3: NO COVERAGE (0)" "$F3" "gaps" "NO COVERAGE (0)"
# A structural tag proves the tag exists, not that the test ran: with no
# ingested result and no CSV row it is UNVERIFIED-RESULT (non-blocking).
check_contains "REQ-V2C-02: Fixture 3: tagged but never-run requirement listed under UNVERIFIED-RESULT" "$F3" "gaps" "REQ-FIX-02"

# ---- Fixture 3b: a comment next to a test is NOT a structural tag ----
F3B="$SCRATCH/f3b_comment_only"
make_repo "$F3B"
write_spec "$F3B" FIX-1 REQ-FIX-02 "Something only a comment points at"
mkdir -p "$F3B/tests"
cat > "$F3B/tests/test_demo.py" <<'EOF'
# covers REQ-FIX-02
def test_demo():
    assert True
EOF
commit_all "$F3B" -m "FIX-1: comment-only link"
check_exit "REQ-V2C-04: Fixture 3b: comment adjacent to a test is not coverage -> exit 1" "$F3B" "gaps" 1

# ---- Fixture 4: ID + the word "test" in the same file, no structural link ----
F4="$SCRATCH/f4_loose_match"
make_repo "$F4"
write_spec "$F4" FIX-1 REQ-FIX-03 "Something merely mentioned near the word test"
mkdir -p "$F4/tests"
cat > "$F4/tests/test_unrelated.py" <<'EOF'
"""
This test module is unrelated. It just happens to mention REQ-FIX-03 in
passing, in a paragraph that also contains the word test, with no actual
test function tagged to it, no decorator, no docstring on a specific test.
"""
def test_something_else():
    assert True
EOF
commit_all "$F4" -m "FIX-1: add spec and an unrelated test mentioning the ID in passing"
check_exit "REQ-CLI-02: Fixture 4: loose mention (not structural) -> still exit 1" "$F4" "gaps" 1
check_contains "REQ-CLI-02: Fixture 4: mentioned requirement still listed as NO COVERAGE" "$F4" "gaps" "REQ-FIX-03"

# ---- Fixture 5: CSV claims a test_case_id NOT in the named file -> NOT coverage ----
F5="$SCRATCH/f5_csv_uncorroborated"
make_repo "$F5"
write_spec "$F5" FIX-1 REQ-FIX-04 "Something the CSV claims is tested, but isn't really"
mkdir -p "$F5/validation"
echo "print('this file never mentions the case id or requirement id')" > "$F5/run.py"
cat > "$F5/validation/traceability.csv" <<'EOF'
tracker_key,requirement_id,requirement_summary,spec_commit,implementing_commits,test_case_id,automated_test,test_run_id,result,evidence_link,risk_tier,revalidation
FIX-1,REQ-FIX-04,claims coverage,abc123,def456,CASE-1,run.py,run-1,PASS,see run.py,1,None
EOF
commit_all "$F5" -m "FIX-1: add spec + an uncorroborated CSV claim"
check_exit "REQ-CLI-03: Fixture 5: uncorroborated CSV claim -> still exit 1" "$F5" "gaps" 1
check_contains "REQ-CLI-03: Fixture 5: listed as NO COVERAGE with the reason" "$F5" "gaps" "could not be independently verified"

# ---- Fixture 6: CSV claims a test_case_id that IS in the named file -> covered ----
F6="$SCRATCH/f6_csv_corroborated"
make_repo "$F6"
write_spec "$F6" FIX-1 REQ-FIX-05 "Something the CSV claims is tested, and genuinely is"
mkdir -p "$F6/validation"
echo "# this file genuinely contains CASE-2 and REQ-FIX-05" > "$F6/run.py"
cat > "$F6/validation/traceability.csv" <<'EOF'
tracker_key,requirement_id,requirement_summary,spec_commit,implementing_commits,test_case_id,automated_test,test_run_id,result,evidence_link,risk_tier,revalidation
FIX-1,REQ-FIX-05,genuinely covered,abc123,def456,CASE-2,run.py,run-1,PASS,see run.py,1,None
EOF
commit_all "$F6" -m "FIX-1: add spec + a corroborated CSV claim"
check_exit "REQ-CLI-03: Fixture 6: corroborated CSV claim -> exit 0" "$F6" "gaps" 0
check_contains "REQ-CLI-03: Fixture 6: NO COVERAGE (0)" "$F6" "gaps" "NO COVERAGE (0)"

# ---- Fixture 7: structural tag + a CSV row recording PASS, no ingested result:
# not UNVERIFIED-RESULT (a result was recorded) but SELF-ASSERTED (nothing
# machine-readable corroborates it). Non-blocking by default; --strict blocks.
F7="$SCRATCH/f7_structural_with_recorded_result"
make_repo "$F7"
write_spec "$F7" FIX-1 REQ-FIX-06 "Something structurally tested AND with a recorded run result"
mkdir -p "$F7/tests" "$F7/validation" && cp "$FIX/tagged/test_demo_fix06.py" "$F7/tests/"
cat > "$F7/validation/traceability.csv" <<'EOF'
tracker_key,requirement_id,requirement_summary,spec_commit,implementing_commits,test_case_id,automated_test,test_run_id,result,evidence_link,risk_tier,revalidation
FIX-1,REQ-FIX-06,structural plus recorded result,abc123,def456,CASE-3,tests/test_demo_fix06.py,run-1,PASS,see test_demo_fix06.py,1,None
EOF
commit_all "$F7" -m "FIX-1: add spec, tagged test, and a CSV row recording its result"
check_exit "REQ-CLI-01: Fixture 7: structural tie + recorded CSV result -> exit 0" "$F7" "gaps" 0
check_contains "REQ-V2C-02: Fixture 7: UNVERIFIED-RESULT (0)" "$F7" "gaps" "UNVERIFIED-RESULT (0)"
check_contains "REQ-V2C-02: Fixture 7: free-text CSV PASS is reported as SELF-ASSERTED" "$F7" "gaps" "SELF-ASSERTED (1)"
check_exit "REQ-V2C-02: Fixture 7: --strict makes SELF-ASSERTED blocking -> exit 1" "$F7" "gaps --strict" 1

# ---- Fixture 8: a malformed traceability.csv is never parsed into findings ----
F8="$SCRATCH/f8_malformed_csv"
make_repo "$F8"
write_spec "$F8" FIX-1 REQ-FIX-07 "Something with a malformed CSV sitting next to it"
mkdir -p "$F8/validation"
printf 'not,even,csv,columns\n1,2,3,4\n' > "$F8/validation/traceability.csv"
commit_all "$F8" -m "FIX-1: add spec + a malformed traceability.csv"
check_exit "REQ-CLI-01: Fixture 8: malformed CSV -> gaps still exits 1 (real NO COVERAGE), not a crash" "$F8" "gaps" 1
check_contains "REQ-CLI-03: Fixture 8: gaps warns about the malformed header" "$F8" "gaps" "WARNING: validation/traceability.csv exists but its header does not contain 'requirement_id'"
check_contains "REQ-CLI-04: Fixture 8: doctor reports the header check as a critical FAIL" "$F8" "doctor" "[FAIL] validation/traceability.csv header is valid"
check_exit "REQ-CLI-06: Fixture 8: export --write refuses rather than risk overwriting it" "$F8" "export --write" 1
check_file "REQ-CLI-06: Fixture 8: malformed CSV left untouched on disk after refused export --write" "$F8/validation/traceability.csv" "not,even,csv,columns"

# ---- Fixture 9: the same requirement ID defined in two spec files -> DUPLICATE-ID ----
F9="$SCRATCH/f9_duplicate_id"
make_repo "$F9"
mkdir -p "$F9/intent/2026-01-01-first" "$F9/intent/2026-02-01-second"
cat > "$F9/intent/2026-01-01-first/spec.md" <<'EOF'
# Spec: First
Tracker: FIX-1

## Requirements
| ID | Requirement | Source | Acceptance |
| --- | --- | --- | --- |
| REQ-FIX-08 | The original definition of this ID | intent.md | it works |
EOF
cat > "$F9/intent/2026-02-01-second/spec.md" <<'EOF'
# Spec: Second
Tracker: FIX-1

## Requirements
| ID | Requirement | Source | Acceptance |
| --- | --- | --- | --- |
| REQ-FIX-08 | A completely different requirement reusing the same ID by mistake | intent.md | it works too |
EOF
commit_all "$F9" -m "FIX-1: add two spec files that both define the same ID"
check_contains "REQ-CLI-02: Fixture 9: duplicate ID surfaced under DUPLICATE-ID" "$F9" "gaps" "REQ-FIX-08: defined in"
check_contains "REQ-CLI-02: Fixture 9: both spec files named in the DUPLICATE-ID entry" "$F9" "gaps" "intent/2026-01-01-first/spec.md, intent/2026-02-01-second/spec.md"

# ---- Fixture 10: every structural form is recognised; comments and prose are not ----
F10="$SCRATCH/f10_structural_forms"
make_repo "$F10"
write_spec "$F10" FIX-1 \
  REQ-FIX-10 "pytest marker" REQ-FIX-11 "test name token" REQ-FIX-12 "it() title" \
  REQ-FIX-13 "Playwright tag" REQ-FIX-14 "JUnit @Tag" REQ-FIX-15 "eval covers frontmatter" \
  REQ-FIX-16 "python comment only" REQ-FIX-17 "js comment only" REQ-FIX-18 "eval prose only" \
  REQ-FIX-19 "commented-out test call"
cp -R "$FIX/structural/." "$F10/"
commit_all "$F10" -m "FIX-1: structural forms"
check_contains "REQ-V2C-04: Fixture 10: six structural forms covered, four non-structural not" "$F10" "gaps" "NO COVERAGE (4)"
check_contains "REQ-V2C-04: Fixture 10: python comment is not coverage" "$F10" "gaps" "  - REQ-FIX-16"
check_contains "REQ-V2C-04: Fixture 10: js comment is not coverage" "$F10" "gaps" "  - REQ-FIX-17"
check_contains "REQ-V2C-04: Fixture 10: eval prompt prose is not coverage" "$F10" "gaps" "  - REQ-FIX-18"
check_contains "REQ-V2C-04: Fixture 10: a commented-out test call is not coverage" "$F10" "gaps" "  - REQ-FIX-19"

# ---- Fixture 11: .evidenceignore removes fixture directories from the scan ----
F11="$SCRATCH/f11_evidenceignore"
make_repo "$F11"
write_spec "$F11" FIX-1 REQ-FIX-02 "Something with a real, tagged test"
mkdir -p "$F11/tests/fixtures" && cp "$FIX/tagged/test_demo_fix02.py" "$F11/tests/"
cp "$FIX/tagged/test_orphan.py" "$F11/tests/fixtures/"
commit_all "$F11" -m "FIX-1: a fixture file tagging an unknown ID"
check_contains "REQ-V2C-04: Fixture 11: without .evidenceignore the fixture is ORPHANED" "$F11" "gaps" "tests/fixtures/test_orphan.py -> REQ-FIX-99"
printf '# fixtures\ntests/fixtures/\n' > "$F11/.evidenceignore"
check_contains "REQ-V2C-04: Fixture 11: with .evidenceignore it is not scanned" "$F11" "gaps" "ORPHANED (0)"

# ---- Fixture 12: JUnit ingestion -> PROVEN / FAILED; --results and adapter ----
F12="$SCRATCH/f12_junit"
make_repo "$F12"
write_spec "$F12" FIX-1 REQ-FIX-20 "Something with a machine-readable result"
mkdir -p "$F12/tests" "$F12/validation" "$F12/reports"
cp "$FIX/tagged/test_ingest.py" "$F12/tests/"
cat > "$F12/validation/traceability.csv" <<'EOF'
tracker_key,requirement_id,requirement_summary,spec_commit,implementing_commits,test_case_id,automated_test,test_run_id,result,evidence_link,risk_tier,revalidation
FIX-1,REQ-FIX-20,Something with a machine-readable result,,,,tests/test_ingest.py,,PASS,,1,
EOF
commit_all "$F12" -m "FIX-1: tagged test + CSV PASS"
check_contains "REQ-V2C-02: Fixture 12: no ingested result -> SELF-ASSERTED" "$F12" "gaps" "SELF-ASSERTED (1)"
cp "$FIX/junit/pass.xml" "$F12/reports/pass.xml"
check_contains "REQ-V2C-02: Fixture 12: --results with a passing JUnit testcase -> PROVEN" "$F12" "gaps --results reports/pass.xml" "PROVEN (1)"
check_contains "REQ-V2C-02: Fixture 12: ingested pass clears SELF-ASSERTED" "$F12" "gaps --results reports/pass.xml" "SELF-ASSERTED (0)"
check_exit "REQ-V2C-02: Fixture 12: --strict passes once every requirement is PROVEN" "$F12" "gaps --strict --results reports/pass.xml" 0
cp "$FIX/junit/fail.xml" "$F12/reports/fail.xml"
check_exit "REQ-V2C-02: Fixture 12: a later failing run of the covering test -> FAILED, exit 1" "$F12" "gaps --results reports" 1
check_contains "REQ-V2C-02: Fixture 12: FAILED names the failing testcase" "$F12" "gaps --results reports" "REQ-FIX-20: ingested result FAILED"
rm "$F12/reports/fail.xml"
printf 'test_results_location: reports\n' > "$F12/.evidence-adapter.tmp"
mkdir -p "$F12/.evidence" && mv "$F12/.evidence-adapter.tmp" "$F12/.evidence/adapter.yml"
check_contains "REQ-V2C-02 REQ-CLI-05: Fixture 12: adapter test_results_location is ingested" "$F12" "gaps" "PROVEN (1)"
cp "$FIX/junit/entity.xml" "$F12/reports/entity.xml"
check_contains "REQ-V2C-02: Fixture 12: XML with DOCTYPE/ENTITY is refused, not parsed" "$F12" "gaps" "1 results file(s) unparseable"

# ---- Fixture 13: claude plugin eval results + covers: frontmatter -> PROVEN ----
F13="$SCRATCH/f13_eval"
make_repo "$F13"
write_spec "$F13" FIX-1 REQ-FIX-30 "An eval-proven behaviour"
mkdir -p "$F13/plugins/demo/evals/demo-case" "$F13/plugins/demo/evals/results/run1"
cp "$FIX/evals/demo-case/prompt.md" "$F13/plugins/demo/evals/demo-case/"
cp "$FIX/evals/aggregate-result.json" "$F13/plugins/demo/evals/results/run1/"
commit_all "$F13" -m "FIX-1: eval case + result"
check_contains "REQ-V2C-02 REQ-V2C-04: Fixture 13: passing eval case with covers: -> PROVEN" "$F13" "gaps" "PROVEN (1)"

# ---- Fixture 14: adapter overrides (patterns, spec_glob, test dirs) ----
F14="$SCRATCH/f14_adapter"
make_repo "$F14"
mkdir -p "$F14/.evidence" "$F14/docs" "$F14/spec"
cat > "$F14/.evidence/adapter.yml" <<'EOF'
requirements_source: file_glob
spec_glob:
  - docs/requirements.md
requirement_pattern: "US-[0-9]+"
tracker_pattern: "[A-Z]+-[0-9]+"
test_dir_segments: [spec]
test_results_location: none
EOF
cat > "$F14/docs/requirements.md" <<'EOF'
| ID | Story |
| --- | --- |
| US-101 | A user story in a custom location |
EOF
cat > "$F14/spec/stories.rb" <<'EOF'
describe "checkout" do
  it("US-101 lets the user pay") { expect(true).to be true }
end
EOF
commit_all "$F14" -m "SHOP-1: custom layout"
check_contains "REQ-CLI-05 REQ-V2C-08: Fixture 14: adapter requirement_pattern/spec_glob/test_dir_segments honoured" "$F14" "gaps" "NO COVERAGE (0)"
check_contains "REQ-CLI-05: Fixture 14: custom-pattern requirement counted" "$F14" "gaps" "Assessment basis: 1 requirements"

# ---- Fixture 15: doctor WARN/FAIL semantics ----
F15="$SCRATCH/f15_doctor"
make_repo "$F15"
mkdir -p "$F15/.evidence/context" "$F15/plugins/evidence-compliance/skills/regulatory-controls/references"
for p in stack deployment toolchain; do echo "# $p   Established: $(date +%Y-%m-%d)" > "$F15/.evidence/context/$p.md"; done
cat > "$F15/.evidence/context/compliance.md" <<'EOF'
# compliance   Established: 2026-09-20
- [ASK] industry: not established

## Applicable frameworks
| Framework | Role | Control set to load | Named owner |
| --- | --- | --- | --- |
| SOC 2 | customer contract | soc2.md | Jane |

## Explicitly out of scope
| Framework | Why |
| --- | --- |
| HIPAA | hipaa.md -- no PHI |
EOF
printf '# SOC 2\n> Owner: UNASSIGNED -- assign one.\n' > "$F15/plugins/evidence-compliance/skills/regulatory-controls/references/soc2.md"
printf '# HIPAA\n> Owner: UNASSIGNED -- assign one.\n' > "$F15/plugins/evidence-compliance/skills/regulatory-controls/references/hipaa.md"
printf '# README\n> Owner: UNASSIGNED\n' > "$F15/plugins/evidence-compliance/skills/regulatory-controls/references/README.md"
commit_all "$F15" -m "FIX-1: doctor fixture"
check_contains "REQ-V2C-05: Fixture 15: unresolved [ASK] is a WARN, not a PASS" "$F15" "doctor" "[WARN] unresolved [ASK] count across profiles"
check_contains "REQ-V2C-05: Fixture 15: missing profiles are a WARN that lists them" "$F15" "doctor" "missing: design-system.md"
check_contains "REQ-V2C-05 REQ-V2O-03: Fixture 15: referenced control set with Owner UNASSIGNED warns" "$F15" "doctor" "unassigned owner in: soc2.md"
check_not_contains "REQ-V2O-03: Fixture 15: out-of-scope sets and README are not flagged" "$F15" "doctor" "hipaa.md,"
check_exit "REQ-V2C-05 REQ-V2C-08: Fixture 15: WARN only -> exit 0" "$F15" "doctor" 0
check_exit "REQ-V2C-05: Fixture 15: --strict turns WARN into exit 1" "$F15" "doctor --strict" 1
check_contains "REQ-V2C-05 REQ-CLI-04: Fixture 15: python3 check present" "$F15" "doctor" "[PASS] python3 resolves on PATH"
# exec-form hook: `bash -c '<inline code>' <script>` -- the inline code is not a path
mkdir -p "$F15/plugins/demo/hooks" "$F15/plugins/demo/scripts"
echo 'print("ok")' > "$F15/plugins/demo/scripts/check.py"
cat > "$F15/plugins/demo/hooks/hooks.json" <<'EOF'
{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "bash",
  "args": ["-c", "command -v python3 >/dev/null 2>&1 && exec python3 \"$0\" || cat >/dev/null",
           "${CLAUDE_PLUGIN_ROOT}/scripts/check.py"]}]}]}}
EOF
check_contains "REQ-CLI-04: Fixture 15: exec-form bash -c hook resolves to its script" "$F15" "doctor" "[PASS] every hooks.json parses"
rm "$F15/plugins/demo/scripts/check.py"
check_exit "REQ-CLI-04: Fixture 15: a hook referencing a missing script is a FAIL -> exit 1" "$F15" "doctor" 1

# ---- Fixture 16: export --write merges; never overwrites or deletes ----
F16="$SCRATCH/f16_export_merge"
make_repo "$F16"
write_spec "$F16" FIX-1 REQ-FIX-40 "Derived summary from the spec" REQ-FIX-41 "A brand new requirement"
mkdir -p "$F16/validation"
cat > "$F16/validation/traceability.csv" <<'EOF'
tracker_key,requirement_id,requirement_summary,spec_commit,implementing_commits,test_case_id,automated_test,test_run_id,result,evidence_link,risk_tier,revalidation
FIX-1,REQ-FIX-40,Human-written summary,,,,,run-77,PASS (manual),https://ci.example/run/77,2,
OLD-1,REQ-OLD-01,A requirement no spec mentions any more,,,,,,PASS,https://ci.example/run/1,1,
EOF
commit_all "$F16" -m "FIX-1: spec + existing matrix"
check_exit "REQ-V2C-06 REQ-V2O-04 REQ-CLI-06 REQ-V2C-08: Fixture 16: export --write succeeds" "$F16" "export --write" 0
check_contains "REQ-V2C-06: Fixture 16: conflicts are reported on stdout" "$F16" "export --write" "REQ-FIX-40 evidence_link: kept 'https://ci.example/run/77' (derived 'NO COVERAGE')"
check_file "REQ-V2C-06: Fixture 16: existing evidence_link not overwritten" "$F16/validation/traceability.csv" "https://ci.example/run/77"
check_file "REQ-V2C-06: Fixture 16: existing requirement_summary not overwritten" "$F16/validation/traceability.csv" "Human-written summary"
check_file "REQ-V2C-06: Fixture 16: existing result and test_run_id not overwritten" "$F16/validation/traceability.csv" "run-77,PASS (manual)"
check_file "REQ-V2C-06 REQ-CLI-06: Fixture 16: a row no spec mentions is never deleted" "$F16/validation/traceability.csv" "REQ-OLD-01,A requirement no spec mentions any more"
check_file "REQ-V2C-06: Fixture 16: a new requirement is appended" "$F16/validation/traceability.csv" "REQ-FIX-41,A brand new requirement"
check_exit "REQ-V2C-06: Fixture 16: --conflicts-only exits 1 while conflicts exist" "$F16" "export --conflicts-only" 1
check_contains "REQ-V2C-06: Fixture 16: --conflicts-only lists the summary conflict" "$F16" "export --conflicts-only" "REQ-FIX-40 requirement_summary: kept 'Human-written summary'"

# ---- Fixture 17: approved_by, agent_sessions, implementing_commits ----
F17="$SCRATCH/f17_matrix_columns"
make_repo "$F17"
write_spec "$F17" FIX-1 REQ-FIX-50 "Something approved and implemented by an agent"
commit_all "$F17" -m "FIX-1: spec"
mkdir -p "$F17/tests" "$F17/src" "$F17/plan" "$F17/.evidence/changes/FIX-1"
cp "$FIX/tagged/test_impl.py" "$F17/tests/"
echo "plan body" > "$F17/plan/FIX-1.md"
PLAN_SHA=$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$F17/plan/FIX-1.md")
cat > "$F17/.evidence/changes/FIX-1/approval.json" <<EOF
{"key":"FIX-1","plan_path":"plan/FIX-1.md","plan_sha256":"$PLAN_SHA","approver":"dana","method":"terminal","approved_at":"2026-09-24T09:00:00Z"}
EOF
echo "x = 1" > "$F17/src/impl.py"
commit_all "$F17" -m "FIX-1: implement" -m "Agent-Session: sess-abc123"
echo "y = 2" > "$F17/src/other.py"
commit_all "$F17" -m "OTHER-9: unrelated" -m "Claude-Session: https://claude.ai/code/session_zzz"
IMPL_SHA=$(git -C "$F17" log --format=%H --grep '^FIX-1: implement' | head -1 | cut -c1-10)
SPEC_FULL=$(git -C "$F17" log --format=%H --grep '^FIX-1: spec' | head -1)
check_contains "REQ-V2C-03: Fixture 17: approved_by from approval.json" "$F17" "export" "dana (terminal, 2026-09-24T09:00:00Z)"
check_contains "REQ-V2C-03: Fixture 17: agent_sessions from commit trailers" "$F17" "export" "Agent-Session: sess-abc123"
check_not_contains "REQ-V2C-03: Fixture 17: another key's session is not attributed" "$F17" "export" "session_zzz"
check_contains "REQ-V2C-03: Fixture 17: implementing_commits lists the keyed commit" "$F17" "export" "$IMPL_SHA"
# spec_commit cell, then an implementing_commits cell holding exactly the one
# implementing commit -- the spec commit (same key) is excluded.
check_contains "REQ-V2C-03: Fixture 17: implementing_commits excludes the spec commit" "$F17" "export" "$SPEC_FULL,$IMPL_SHA,"
export EVIDENCE_GH="$FIX/fake-gh.sh"
check_contains "REQ-V2C-03: Fixture 17: --github adds PR approvals for PRs titled with the key" "$F17" "export --github" "github:alice (PR #7)"
check_not_contains "REQ-V2C-03: Fixture 17: approvals on PRs without the key are ignored" "$F17" "export --github" "mallory"
echo "plan body edited after approval" > "$F17/plan/FIX-1.md"
check_contains "REQ-V2C-03: Fixture 17: approval of an edited plan is shown STALE" "$F17" "export" "STALE: plan changed since approval"

# ---- Fixture 18: tracker check/link through a mocked gh ----
F18="$SCRATCH/f18_tracker"
make_repo "$F18"
mkdir -p "$F18/.evidence"
printf 'tracker: github\ntracker_key_to_issue: GH-(\\d+)\n' > "$F18/.evidence/adapter.yml"
commit_all "$F18" -m "GH-42: adapter"
export FAKE_GH_LOG="$SCRATCH/gh.log"
check_exit "REQ-V2C-10: Fixture 18: tracker check of an existing issue -> exit 0" "$F18" "tracker check GH-42" 0
check_contains "REQ-V2C-10: Fixture 18: tracker check prints the issue" "$F18" "tracker check GH-42" "FOUND: GH-42 -> issue #42 [OPEN] Demo issue"
check_exit "REQ-V2C-10: Fixture 18: tracker check of a missing issue -> exit 1" "$F18" "tracker check GH-404" 1
check_exit "REQ-V2C-10: Fixture 18: tracker link writes back -> exit 0" "$F18" "tracker link GH-42 https://ci.example/run/9" 0
check_file "REQ-V2C-10: Fixture 18: link sent as an issue comment through gh" "$FAKE_GH_LOG" "issue comment 42 --body Evidence link (GH-42): https://ci.example/run/9"
check_exit "REQ-V2C-10: Fixture 18: a key not matching tracker_key_to_issue -> exit 2" "$F18" "tracker check PROJ-1" 2
unset EVIDENCE_GH FAKE_GH_LOG

# ---- Fixture 19: --repos A,B checks PARENT/CHILD chains ----
R_API="$SCRATCH/f19/api"; R_WEB="$SCRATCH/f19/web"; R_OPS="$SCRATCH/f19/ops"
make_repo "$R_API"; make_repo "$R_WEB"; make_repo "$R_OPS"
for r in "$R_API" "$R_WEB"; do write_spec "$r" PLAT-100 REQ-FIX-60 "Shared requirement"; done
mkdir -p "$R_API/tests" "$R_WEB/tests"
for r in "$R_API" "$R_WEB"; do
  cp "$FIX/tagged/test_shared.py" "$r/tests/"
done
commit_all "$R_API" -m "PLAT-100/API-204: api half"
commit_all "$R_WEB" -m "PLAT-100/WEB-17: web half"
echo "x" > "$R_OPS/x.txt"; commit_all "$R_OPS" -m "PLAT-100: ops touched, no child key"
check_exit "REQ-V2X-02 REQ-CLI-07 REQ-V2C-08: Fixture 19: both participants carry a child chain -> exit 0" "$SCRATCH" "gaps --repos $R_API,$R_WEB" 0
check_contains "REQ-V2X-02: Fixture 19: MISSING-CHILD (0) when complete" "$SCRATCH" "gaps --repos $R_API,$R_WEB" "MISSING-CHILD (0)"
check_exit "REQ-V2X-02: Fixture 19: a participant without a child chain -> exit 1" "$SCRATCH" "gaps --repos $R_API,$R_WEB,$R_OPS" 1
check_contains "REQ-V2X-02: Fixture 19: MISSING-CHILD names the parent and the repo" "$SCRATCH" "gaps --repos $R_API,$R_WEB,$R_OPS" "PLAT-100: no child chain in ops"
check_contains "REQ-CLI-07: Fixture 19: scan --repos DIR joins sibling repos on the parent key" "$SCRATCH" "scan --repos $SCRATCH/f19" "PLAT-100: api, ops, web"

echo
echo "==================================="
echo "$pass passed, $fail failed"
if [ -n "${JUNIT_OUT:-}" ]; then
  mkdir -p "$(dirname "$JUNIT_OUT")"
  {
    echo '<?xml version="1.0" encoding="utf-8"?>'
    echo "<testsuites>"
    echo "  <testsuite name=\"cli-fixtures\" tests=\"$((pass + fail))\" failures=\"$fail\" timestamp=\"$(date -u +%Y-%m-%dT%H:%M:%S)\">"
    printf '%s' "$JUNIT_CASES"
    echo "  </testsuite>"
    echo "</testsuites>"
  } > "$JUNIT_OUT"
  echo "JUnit written to $JUNIT_OUT"
fi
[ "$fail" -gt 0 ] && exit 1
exit 0
