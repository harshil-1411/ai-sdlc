#!/bin/bash
# Regression fixtures for the item-1 fix: "gaps reports fully covered on a
# repository with no tests." Six cases must never regress. Tagged against
# cli/REVIEW-BRIEF.md's retrospective spec (intent/<date>-evidence-cli/spec.md):
#   1. requirements + no tests at all           -> ALL uncovered, exit 1
#   2. no requirements anywhere                 -> exit 2, "nothing to assess"
#   3. a requirement + a genuinely, structurally
#      linked test                              -> covered, exit 0
#   4. a requirement ID merely co-located with the word "test" in the same
#      file, with no structural link            -> NOT coverage (still exit 1)
#   5. a traceability.csv row claiming a test_case_id NOT actually present in
#      the named automated_test file            -> NOT coverage (still exit 1)
#   6. a traceability.csv row claiming a test_case_id that IS present in the
#      named automated_test file                -> covered, exit 0
set -u
CLI="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/evidence"
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

pass=0
fail=0

make_repo() {
  local dir="$1"
  mkdir -p "$dir"
  git -C "$dir" init -q -b main
  git -C "$dir" -c user.email=t@t.com -c user.name=t commit -q --allow-empty -m init
}

check_exit() {
  local label="$1" dir="$2" cmd="$3" expected="$4"
  local out status
  out=$(cd "$dir" && python3 "$CLI" $cmd 2>&1)
  status=$?
  if [ "$status" = "$expected" ]; then
    pass=$((pass + 1))
    echo "PASS: $label (exit $status)"
  else
    fail=$((fail + 1))
    echo "FAIL: $label (expected exit $expected, got $status) -- output:"
    echo "$out" | sed 's/^/    /'
  fi
}

check_contains() {
  local label="$1" dir="$2" cmd="$3" needle="$4"
  local out
  out=$(cd "$dir" && python3 "$CLI" $cmd 2>&1)
  if echo "$out" | grep -qF "$needle"; then
    pass=$((pass + 1))
    echo "PASS: $label"
  else
    fail=$((fail + 1))
    echo "FAIL: $label -- expected to find: $needle"
    echo "$out" | sed 's/^/    /'
  fi
}

# covers REQ-CLI-01 (gaps distinguishes exit 0/1/2, never rendering two the same)
# ---- Fixture 1: requirements, no tests at all -> all uncovered, exit 1 ----
F1="$SCRATCH/f1_no_tests"
make_repo "$F1"
mkdir -p "$F1/intent/2026-01-01-demo"
cat > "$F1/intent/2026-01-01-demo/spec.md" <<'EOF'
# Spec: Demo
Tracker: FIX-1

## Requirements
| ID | Requirement | Source | Acceptance |
| --- | --- | --- | --- |
| REQ-FIX-01 | Something with no test anywhere | intent.md | it works |
EOF
git -C "$F1" add -A && git -C "$F1" -c user.email=t@t.com -c user.name=t commit -q -m "FIX-1: add spec, no tests"
check_exit "Fixture 1: requirement with no test -> exit 1" "$F1" "gaps" 1
check_contains "Fixture 1: REQ-FIX-01 listed as NO COVERAGE" "$F1" "gaps" "REQ-FIX-01"

# ---- Fixture 2: no requirements anywhere -> exit 2 ----
F2="$SCRATCH/f2_empty"
make_repo "$F2"
echo "hello" > "$F2/README.md"
git -C "$F2" add -A && git -C "$F2" -c user.email=t@t.com -c user.name=t commit -q -m "init readme"
check_exit "Fixture 2: no requirements anywhere -> exit 2" "$F2" "gaps" 2
check_contains "Fixture 2: says 'nothing to assess'" "$F2" "gaps" "Nothing to assess"

# covers REQ-CLI-02 (coverage requires a structural tie -- name/tag/annotation/
# docstring/decorator adjacent to a real test declaration, not mere proximity)
# ---- Fixture 3: a requirement with a genuinely, structurally linked test -> exit 0 ----
F3="$SCRATCH/f3_covered"
make_repo "$F3"
mkdir -p "$F3/intent/2026-01-01-demo" "$F3/tests"
cat > "$F3/intent/2026-01-01-demo/spec.md" <<'EOF'
# Spec: Demo
Tracker: FIX-1

## Requirements
| ID | Requirement | Source | Acceptance |
| --- | --- | --- | --- |
| REQ-FIX-02 | Something with a real, tagged test | intent.md | it works |
EOF
cat > "$F3/tests/test_demo.py" <<'EOF'
# covers REQ-FIX-02
def test_demo():
    assert True
EOF
git -C "$F3" add -A && git -C "$F3" -c user.email=t@t.com -c user.name=t commit -q -m "FIX-1: add spec and a real tagged test"
check_exit "Fixture 3: structurally-tagged test -> exit 0" "$F3" "gaps" 0
check_contains "Fixture 3: NO COVERAGE (0)" "$F3" "gaps" "NO COVERAGE (0)"

# ---- Fixture 4: loose-match regression -- REQ ID + word "test" in the same
# file, but no structural link -> must NOT count as coverage ----
F4="$SCRATCH/f4_loose_match"
make_repo "$F4"
mkdir -p "$F4/intent/2026-01-01-demo" "$F4/tests"
cat > "$F4/intent/2026-01-01-demo/spec.md" <<'EOF'
# Spec: Demo
Tracker: FIX-1

## Requirements
| ID | Requirement | Source | Acceptance |
| --- | --- | --- | --- |
| REQ-FIX-03 | Something merely mentioned near the word test | intent.md | it works |
EOF
cat > "$F4/tests/test_unrelated.py" <<'EOF'
"""
This test module is unrelated. It just happens to mention REQ-FIX-03 in
passing, in a paragraph that also contains the word test, with no actual
test function tagged to it, no decorator, no docstring on a specific test.
"""
def test_something_else():
    assert True
EOF
git -C "$F4" add -A && git -C "$F4" -c user.email=t@t.com -c user.name=t commit -q -m "FIX-1: add spec and an unrelated test mentioning the ID in passing"
check_exit "Fixture 4: loose mention (not structural) -> still exit 1" "$F4" "gaps" 1
check_contains "Fixture 4: REQ-FIX-03 listed as NO COVERAGE despite the mention" "$F4" "gaps" "REQ-FIX-03"

# covers REQ-CLI-03 (a traceability.csv claim is only trusted if independently
# corroborated against the automated_test file it names)
# ---- Fixture 5: CSV claims a test_case_id that is NOT in the named file -> NOT coverage ----
F5="$SCRATCH/f5_csv_uncorroborated"
make_repo "$F5"
mkdir -p "$F5/intent/2026-01-01-demo" "$F5/validation"
cat > "$F5/intent/2026-01-01-demo/spec.md" <<'EOF'
# Spec: Demo
Tracker: FIX-1

## Requirements
| ID | Requirement | Source | Acceptance |
| --- | --- | --- | --- |
| REQ-FIX-04 | Something the CSV claims is tested, but isn't really | intent.md | it works |
EOF
echo "print('this file never mentions the case id or requirement id')" > "$F5/run.py"
cat > "$F5/validation/traceability.csv" <<'EOF'
tracker_key,requirement_id,requirement_summary,spec_commit,implementing_commits,test_case_id,automated_test,test_run_id,result,evidence_link,risk_tier,revalidation
FIX-1,REQ-FIX-04,claims coverage,abc123,def456,CASE-1,run.py,run-1,PASS,see run.py,1,None
EOF
git -C "$F5" add -A && git -C "$F5" -c user.email=t@t.com -c user.name=t commit -q -m "FIX-1: add spec + an uncorroborated CSV claim"
check_exit "Fixture 5: uncorroborated CSV claim -> still exit 1" "$F5" "gaps" 1
check_contains "Fixture 5: REQ-FIX-04 listed as NO COVERAGE with the reason" "$F5" "gaps" "could not be independently verified"

# ---- Fixture 6: CSV claims a test_case_id that IS in the named file -> covered ----
F6="$SCRATCH/f6_csv_corroborated"
make_repo "$F6"
mkdir -p "$F6/intent/2026-01-01-demo" "$F6/validation"
cat > "$F6/intent/2026-01-01-demo/spec.md" <<'EOF'
# Spec: Demo
Tracker: FIX-1

## Requirements
| ID | Requirement | Source | Acceptance |
| --- | --- | --- | --- |
| REQ-FIX-05 | Something the CSV claims is tested, and genuinely is | intent.md | it works |
EOF
echo "# this file genuinely contains CASE-2 and REQ-FIX-05" > "$F6/run.py"
cat > "$F6/validation/traceability.csv" <<'EOF'
tracker_key,requirement_id,requirement_summary,spec_commit,implementing_commits,test_case_id,automated_test,test_run_id,result,evidence_link,risk_tier,revalidation
FIX-1,REQ-FIX-05,genuinely covered,abc123,def456,CASE-2,run.py,run-1,PASS,see run.py,1,None
EOF
git -C "$F6" add -A && git -C "$F6" -c user.email=t@t.com -c user.name=t commit -q -m "FIX-1: add spec + a corroborated CSV claim"
check_exit "Fixture 6: corroborated CSV claim -> exit 0" "$F6" "gaps" 0
check_contains "Fixture 6: NO COVERAGE (0)" "$F6" "gaps" "NO COVERAGE (0)"

echo
echo "==================================="
echo "$pass passed, $fail failed"
[ "$fail" -gt 0 ] && exit 1
exit 0
