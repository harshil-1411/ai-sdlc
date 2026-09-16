#!/bin/bash
# Regression suite for template-sensor.sh -- the one advisory-only sensor in
# this repo, distinct in kind from the six deny-capable gates covered by
# gate-regression-tests.sh. This suite checks for additionalContext in stdout
# on the "finding" cases, and checks stdout is completely EMPTY on every
# "silence" case -- unlike a gate, a sensor with any output on a clean input
# would itself be a bug (unwanted noise on the happy path).
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
SCRIPT="$REPO_ROOT/plugins/evidence-sdlc/scripts/template-sensor.sh"
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

pass=0
fail=0
declare -a failures=()

json_path() {
  python3 -c 'import json,sys; print(json.dumps({"tool_input": {"file_path": sys.argv[1]}}))' "$1"
}

# run_case <label> <target_file_abspath> <expect: silent|finding>
run_case() {
  local label="$1" target="$2" expect="$3"
  local out
  out=$(bash "$SCRIPT" <<<"$(json_path "$target")" 2>&1)
  if [ "$expect" = "silent" ]; then
    if [ -z "$out" ]; then
      pass=$((pass + 1)); echo "PASS: $label"
    else
      fail=$((fail + 1)); failures+=("$label (expected silence, got output)")
      echo "FAIL: $label (expected silence) -- output: $out"
    fi
  else
    if echo "$out" | grep -q '"additionalContext"'; then
      pass=$((pass + 1)); echo "PASS: $label"
    else
      fail=$((fail + 1)); failures+=("$label (expected an additionalContext finding, got: $out)")
      echo "FAIL: $label (expected a finding) -- output: $out"
    fi
  fi
}

echo "=== spec.md: Areas of concern ==="
F1="$SCRATCH/f1"; mkdir -p "$F1"
cat > "$F1/spec.md" <<'EOF'
## Areas of concern
The choice between JWT and session cookies is close; named owner: Security lead.

## Rejected alternatives
None.
EOF
run_case "spec.md with real Areas of concern content -> silent" "$F1/spec.md" silent

F2="$SCRATCH/f2"; mkdir -p "$F2"
cat > "$F2/spec.md" <<'EOF'
## Areas of concern
<Every conflict between standards, every unsatisfiable constraint, each with the
named policy owner who must decide. Do not leave this empty by default.>

## Rejected alternatives
None.
EOF
run_case "spec.md with unfilled placeholder -> finding" "$F2/spec.md" finding

F3="$SCRATCH/f3"; mkdir -p "$F3"
cat > "$F3/spec.md" <<'EOF'
## Areas of concern

## Rejected alternatives
None.
EOF
run_case "spec.md with an empty section (heading present, no body) -> finding" "$F3/spec.md" finding

echo "=== plan.md: Files claimed (bare form) ==="
F4="$SCRATCH/f4"; mkdir -p "$F4"
cat > "$F4/plan.md" <<'EOF'
## Files claimed
- src/api/orders.py
- src/api/orders_test.py

## Files that change
- src/api/orders.py
EOF
run_case "plan.md with real Files claimed content -> silent" "$F4/plan.md" silent

F5="$SCRATCH/f5"; mkdir -p "$F5"
cat > "$F5/plan.md" <<'EOF'
## Files claimed
<Every path this plan is going to touch, so a concurrent session in another
worktree can see it is already spoken for before it starts.>

## Files that change
EOF
run_case "plan.md with unfilled placeholder -> finding" "$F5/plan.md" finding

echo "=== plan/<TRACKER-KEY>.md: the namespaced concurrent-session form ==="
F6="$SCRATCH/f6"; mkdir -p "$F6/plan"
cat > "$F6/plan/TRACE-99.md" <<'EOF'
## Files claimed
<Every path this plan is going to touch, so a concurrent session in another
worktree can see it is already spoken for before it starts.>
EOF
run_case "namespaced plan/<KEY>.md with unfilled placeholder -> finding" "$F6/plan/TRACE-99.md" finding

F7="$SCRATCH/f7"; mkdir -p "$F7/plan"
cat > "$F7/plan/TRACE-99.md" <<'EOF'
## Files claimed
- src/orders.py
EOF
run_case "namespaced plan/<KEY>.md with real content -> silent" "$F7/plan/TRACE-99.md" silent

echo "=== unrelated files must never fire ==="
F8="$SCRATCH/f8"; mkdir -p "$F8"
echo "# Hello" > "$F8/README.md"
run_case "unrelated file (README.md) -> silent" "$F8/README.md" silent

F9="$SCRATCH/f9"; mkdir -p "$F9"
echo "hello" > "$F9/some_plan.md"
run_case "a file merely named *_plan.md, not in a plan/ dir -> silent" "$F9/some_plan.md" silent

echo "=== jq missing: must degrade to silence, NOT fail closed -- this sensor has nothing to protect ==="
NOJQ_BIN="$SCRATCH/nojq-bin"
mkdir -p "$NOJQ_BIN"
for tool in bash cat awk sed tr; do
  src=$(command -v "$tool") && ln -sf "$src" "$NOJQ_BIN/$(basename "$src")"
done
if PATH="$NOJQ_BIN" command -v jq >/dev/null 2>&1; then
  echo "FATAL: jq is still resolvable under the constructed jq-free PATH ($NOJQ_BIN)."
  echo "The jq-missing case below would be meaningless. Aborting."
  exit 1
fi
out=$(PATH="$NOJQ_BIN" bash "$SCRIPT" <<<"$(json_path "$F2/spec.md")" 2>&1)
status=$?
if [ -z "$out" ] && [ "$status" -eq 0 ]; then
  pass=$((pass + 1)); echo "PASS: jq missing -> silent, exit 0 (not a deny -- nothing to fail closed on here)"
else
  fail=$((fail + 1)); failures+=("jq-missing case (expected silent exit 0, got status=$status output=$out)")
  echo "FAIL: jq missing -> expected silent exit 0, got status=$status output=$out"
fi

echo
echo "==================================="
echo "$pass passed, $fail failed"
if [ "$fail" -gt 0 ]; then
  printf 'FAILED: %s\n' "${failures[@]}"
  exit 1
fi
exit 0
