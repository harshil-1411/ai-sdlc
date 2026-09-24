#!/bin/bash
# Regression suite for the six gate scripts. Originally the true/false-positive
# fixes from PILOT-7 through PILOT-12; later extended with fail-closed-on-
# missing-jq cases (PILOT-18) and the lost-execute-bit case (PILOT-31) that
# proves the PILOT-3 bash-wrapper fix actually holds, not just once by hand.
# Runs each script exactly as the Claude Code hook runtime does -- a JSON payload
# on stdin -- and checks stdout for a deny decision. Isolated in a scratch
# directory (with, where needed, its own throwaway git repo) so results do not
# depend on this repository's own, constantly-changing plan.md files or branch
# state. See TRACE-1 intent.md / spec.md / plan.md for why this exists.
#
# NOTE (documented per plan.md's "Risks" section): block-protected-branch-push.sh
# and require-issue-key.sh depend on the CURRENT branch name via
# `git rev-parse --abbrev-ref HEAD`. This suite creates its own throwaway repo with
# a chosen branch name for each case, so it does not depend on which branch this
# suite itself is run from.
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

pass=0
fail=0
declare -a failures=()

# run_case <label> <script_relpath> <json> <expected: deny|allow> <workdir> [env_assignments]
#
# Deny is detected two ways because the gate scripts use two different hook
# protocols: most emit `{"permissionDecision": "deny"}` as JSON and exit 0
# (the exit code carries no signal); production-gate.sh instead writes plain
# text to stderr and exits non-zero. Both are real, both are checked.
run_case() {
  local label="$1" script="$2" json="$3" expected="$4" workdir="$5" envs="${6:-}"
  local out status got
  out=$(cd "$workdir" && env $envs bash "$REPO_ROOT/$script" <<<"$json" 2>&1)
  status=$?
  got="allow"
  if echo "$out" | grep -q '"permissionDecision": *"deny"'; then
    got="deny"
  elif [ "$status" -ne 0 ]; then
    got="deny"
  fi
  if [ "$got" = "$expected" ]; then
    pass=$((pass + 1))
    echo "PASS: $label"
  else
    fail=$((fail + 1))
    failures+=("$label (expected $expected, got $got)")
    echo "FAIL: $label (expected $expected, got $got) -- output: $out"
  fi
}

json_path() {
  python3 -c 'import json,sys; print(json.dumps({"tool_input": {"file_path": sys.argv[1]}}))' "$1"
}
json_cmd() {
  python3 -c 'import json,sys; print(json.dumps({"tool_input": {"command": sys.argv[1]}}))' "$1"
}

# run_case_abspath is identical to run_case except it invokes a full, absolute
# script path directly rather than resolving one relative to REPO_ROOT --
# needed for the execute-bit case below, which runs against a scratch COPY of
# a real script (with its execute bit deliberately stripped), never the real
# file in this repository.
run_case_abspath() {
  local label="$1" script_abspath="$2" json="$3" expected="$4" workdir="$5" envs="${6:-}"
  local out status got
  out=$(cd "$workdir" && env $envs bash "$script_abspath" <<<"$json" 2>&1)
  status=$?
  got="allow"
  if echo "$out" | grep -q '"permissionDecision": *"deny"'; then
    got="deny"
  elif [ "$status" -ne 0 ]; then
    got="deny"
  fi
  if [ "$got" = "$expected" ]; then
    pass=$((pass + 1))
    echo "PASS: $label"
  else
    fail=$((fail + 1))
    failures+=("$label (expected $expected, got $got)")
    echo "FAIL: $label (expected $expected, got $got) -- output: $out"
  fi
}

# ---- fresh, empty scratch dir with no plan.md anywhere ----
EMPTY="$SCRATCH/empty"
mkdir -p "$EMPTY"

# ---- scratch dir with a plan.md ONLY at its root (the PILOT-7 bug scenario:
# the other two glob locations have no match) ----
ROOTPLAN="$SCRATCH/rootplan"
mkdir -p "$ROOTPLAN"
: > "$ROOTPLAN/plan.md"

# ---- git repo with plan.md ONLY at its root, for the cwd-anchoring case
# below: gate-plan-exists.sh used to resolve plan.md/intent/*/plan.md relative
# to the tool call's cwd rather than the repo root, so a tool call made from a
# subdirectory (e.g. plugins/<name>/ during plugin development) was falsely
# denied even though an approved plan.md existed at the repo root. Found via
# this plugin's own eval-suite work (see intent/2026-09-12-gate-regression-tests/). ----
SUBDIRPLAN="$SCRATCH/subdirplan"
mkdir -p "$SUBDIRPLAN/plugins/some-plugin"
git -C "$SUBDIRPLAN" init -q -b main
: > "$SUBDIRPLAN/plan.md"

# ---- throwaway git repos with a chosen branch, one real commit ----
make_repo() {
  local dir="$1" branch="$2"
  mkdir -p "$dir"
  git -C "$dir" init -q -b "$branch"
  git -C "$dir" -c user.email=test@test.com -c user.name=test commit -q --allow-empty -m init
}
PROTECTED_REPO="$SCRATCH/protected_repo"
FEATURE_REPO="$SCRATCH/feature_repo"
make_repo "$PROTECTED_REPO" master
make_repo "$FEATURE_REPO" feature-x

# ---- a PATH with bash/git/python3 but no jq resolvable, for the
# fail-closed-on-missing-jq cases added for the audit's Critical Finding #2.
# Every gate script now checks `command -v jq` itself before doing anything
# jq-dependent and denies if it is absent, rather than falling through to an
# empty variable and an unintended default-allow. Sanity-checked below before
# any case trusts it -- a sandbox that silently still resolves jq would make
# every case in this section pass for the wrong reason. ----
NOJQ_BIN="$SCRATCH/nojq-bin"
mkdir -p "$NOJQ_BIN"
for tool in bash git python3; do
  src=$(command -v "$tool") && ln -sf "$src" "$NOJQ_BIN/$(basename "$src")"
done
if PATH="$NOJQ_BIN" command -v jq >/dev/null 2>&1; then
  echo "FATAL: jq is still resolvable under the constructed jq-free PATH ($NOJQ_BIN)."
  echo "The jq-missing fail-closed cases below would be meaningless. Aborting."
  exit 1
fi

echo "=== gate-plan-exists.sh ==="
run_case "gate-plan-exists: no plan.md anywhere -> deny" \
  "plugins/evidence-sdlc/scripts/gate-plan-exists.sh" \
  "$(json_path /repo/src/a.py)" deny "$EMPTY"
run_case "gate-plan-exists: plan.md only at root (PILOT-7 bug scenario) -> allow" \
  "plugins/evidence-sdlc/scripts/gate-plan-exists.sh" \
  "$(json_path /repo/src/a.py)" allow "$ROOTPLAN"
run_case "gate-plan-exists: doc path always exempt -> allow" \
  "plugins/evidence-sdlc/scripts/gate-plan-exists.sh" \
  "$(json_path /repo/README.md)" allow "$EMPTY"
run_case "gate-plan-exists: plan.md at repo root, tool call cwd is a subdirectory -> allow" \
  "plugins/evidence-sdlc/scripts/gate-plan-exists.sh" \
  "$(json_path plugins/some-plugin/src/a.py)" allow "$SUBDIRPLAN/plugins/some-plugin"

echo "=== production-gate.sh ==="
run_case "production-gate: standalone prod token -> deny" \
  "plugins/evidence-sdlc/scripts/production-gate.sh" \
  "$(json_cmd 'kubectl apply -n prod')" deny "$EMPTY"
run_case "production-gate: 'reproduce' substring (PILOT-8 false positive) -> allow" \
  "plugins/evidence-sdlc/scripts/production-gate.sh" \
  "$(json_cmd 'echo let us reproduce the bug')" allow "$EMPTY"
run_case "production-gate: 'byproduct' substring -> allow" \
  "plugins/evidence-sdlc/scripts/production-gate.sh" \
  "$(json_cmd 'echo byproduct of refactor')" allow "$EMPTY"
run_case "production-gate: standalone prod token WITH RELEASE_APPROVAL -> allow" \
  "plugins/evidence-sdlc/scripts/production-gate.sh" \
  "$(json_cmd 'kubectl apply -n prod')" allow "$EMPTY" "RELEASE_APPROVAL=rel-2026-09-12"

echo "=== block-test-weakening.sh (FIX_TASK=1) ==="
run_case "block-test-weakening: real test file, prefix -> deny" \
  "plugins/evidence-sdlc/scripts/block-test-weakening.sh" \
  "$(json_path test_utils.py)" deny "$EMPTY" "FIX_TASK=1"
run_case "block-test-weakening: root-level tests/ dir (was missed pre-fix) -> deny" \
  "plugins/evidence-sdlc/scripts/block-test-weakening.sh" \
  "$(json_path tests/helpers.py)" deny "$EMPTY" "FIX_TASK=1"
run_case "block-test-weakening: 'latest_migration.py' (PILOT-9 false positive) -> allow" \
  "plugins/evidence-sdlc/scripts/block-test-weakening.sh" \
  "$(json_path src/latest_migration.py)" allow "$EMPTY" "FIX_TASK=1"
run_case "block-test-weakening: 'fastest_path.py' (PILOT-9 false positive) -> allow" \
  "plugins/evidence-sdlc/scripts/block-test-weakening.sh" \
  "$(json_path src/fastest_path.py)" allow "$EMPTY" "FIX_TASK=1"
run_case "block-test-weakening: FIX_TASK unset -> always allow regardless of path" \
  "plugins/evidence-sdlc/scripts/block-test-weakening.sh" \
  "$(json_path test_utils.py)" allow "$EMPTY"

echo "=== protect-validated-paths.sh ==="
# CHANGE_TICKET= (empty) is passed explicitly on the two "must deny" cases below
# so this suite is hermetic regardless of what the invoking shell's own
# environment happens to have set -- a session working on this repository
# under a real change ticket (e.g. CHANGE_TICKET=TRACE-1) would otherwise leak
# that value in and turn an expected deny into an allow-with-context, which is
# a test-isolation bug, not a script bug.
run_case "protect-validated-paths: real migrations/ dir -> deny" \
  "plugins/evidence-sdlc/scripts/protect-validated-paths.sh" \
  "$(json_path migrations/0001_init.sql)" deny "$EMPTY" "CHANGE_TICKET="
run_case "protect-validated-paths: root-level audit/ dir (was missed pre-fix) -> deny" \
  "plugins/evidence-sdlc/scripts/protect-validated-paths.sh" \
  "$(json_path audit/report.pdf)" deny "$EMPTY" "CHANGE_TICKET="
run_case "protect-validated-paths: 'cache-invalidation/' (PILOT-10 false positive) -> allow" \
  "plugins/evidence-sdlc/scripts/protect-validated-paths.sh" \
  "$(json_path src/cache-invalidation/store.py)" allow "$EMPTY"
run_case "protect-validated-paths: 'test-infra/' (PILOT-10 false positive) -> allow" \
  "plugins/evidence-sdlc/scripts/protect-validated-paths.sh" \
  "$(json_path src/test-infra/fixtures.py)" allow "$EMPTY"
run_case "protect-validated-paths: migrations/ WITH CHANGE_TICKET -> allow (not a hard deny)" \
  "plugins/evidence-sdlc/scripts/protect-validated-paths.sh" \
  "$(json_path migrations/0001_init.sql)" allow "$EMPTY" "CHANGE_TICKET=CHG-1234"

echo "=== require-issue-key.sh (protected branch) ==="
run_case "require-issue-key: real commit, no key -> deny" \
  "plugins/evidence-quality/scripts/require-issue-key.sh" \
  "$(json_cmd "git commit -m 'no key here'")" deny "$PROTECTED_REPO"
run_case "require-issue-key: real commit, with key -> allow" \
  "plugins/evidence-quality/scripts/require-issue-key.sh" \
  "$(json_cmd "git commit -m 'PILOT-1: has key'")" allow "$PROTECTED_REPO"
run_case "require-issue-key: mere mention in echo (PILOT-11 false positive) -> allow" \
  "plugins/evidence-quality/scripts/require-issue-key.sh" \
  "$(json_cmd 'echo remember to git commit later')" allow "$PROTECTED_REPO"

echo "=== block-protected-branch-push.sh ==="
run_case "block-protected-branch-push: real push on protected branch -> deny" \
  "plugins/evidence-sdlc/scripts/block-protected-branch-push.sh" \
  "$(json_cmd 'git push origin master')" deny "$PROTECTED_REPO"
run_case "block-protected-branch-push: real push on a feature branch -> allow" \
  "plugins/evidence-sdlc/scripts/block-protected-branch-push.sh" \
  "$(json_cmd 'git push origin feature-x')" allow "$FEATURE_REPO"
run_case "block-protected-branch-push: mere mention in echo (PILOT-12 false positive) -> allow" \
  "plugins/evidence-sdlc/scripts/block-protected-branch-push.sh" \
  "$(json_cmd 'echo remember to git push after review')" allow "$PROTECTED_REPO"

echo "=== jq-missing fail-closed cases (audit Critical Finding #2) ==="
run_case "gate-plan-exists: jq missing -> deny (fail closed, not open)" \
  "plugins/evidence-sdlc/scripts/gate-plan-exists.sh" \
  "$(json_path /repo/src/a.py)" deny "$EMPTY" "PATH=$NOJQ_BIN"
run_case "protect-validated-paths: jq missing -> deny (fail closed, not open)" \
  "plugins/evidence-sdlc/scripts/protect-validated-paths.sh" \
  "$(json_path migrations/0001_init.sql)" deny "$EMPTY" "PATH=$NOJQ_BIN"
run_case "block-test-weakening: jq missing, FIX_TASK=1 -> deny (fail closed, not open)" \
  "plugins/evidence-sdlc/scripts/block-test-weakening.sh" \
  "$(json_path test_utils.py)" deny "$EMPTY" "FIX_TASK=1 PATH=$NOJQ_BIN"
run_case "block-test-weakening: jq missing, FIX_TASK unset -> still allow (gate stays inert outside a fix task)" \
  "plugins/evidence-sdlc/scripts/block-test-weakening.sh" \
  "$(json_path test_utils.py)" allow "$EMPTY" "PATH=$NOJQ_BIN"
run_case "block-protected-branch-push: jq missing -> deny (fail closed, not open)" \
  "plugins/evidence-sdlc/scripts/block-protected-branch-push.sh" \
  "$(json_cmd 'git push origin master')" deny "$PROTECTED_REPO" "PATH=$NOJQ_BIN"
run_case "production-gate: jq missing -> deny (fail closed, not open)" \
  "plugins/evidence-sdlc/scripts/production-gate.sh" \
  "$(json_cmd 'kubectl apply -n prod')" deny "$EMPTY" "PATH=$NOJQ_BIN"
run_case "require-issue-key: jq missing -> deny (fail closed, not open)" \
  "plugins/evidence-quality/scripts/require-issue-key.sh" \
  "$(json_cmd "git commit -m 'no key here'")" deny "$PROTECTED_REPO" "PATH=$NOJQ_BIN"

echo "=== lost execute bit (PILOT-3 fix) ==="
# The claim SECURITY.md leads with: a hook script that loses its execute bit
# on extraction -- Claude Code's own plugin zip does this, per SECURITY.md's
# "Using this safely" section -- still runs and still denies, because every
# hooks.json entry in this repo invokes it as `command: "bash",
# args: ["<script>"]`, never as the script's own executable. Verified once by
# hand during PILOT-3 (see plan.md's Risks section); never a repeatable case
# until now -- raised in response to external review of this repository.
EXECBIT_SCRIPT="$SCRATCH/gate-plan-exists-no-exec-bit.sh"
cp "$REPO_ROOT/plugins/evidence-sdlc/scripts/gate-plan-exists.sh" "$EXECBIT_SCRIPT"
chmod -x "$EXECBIT_SCRIPT"
if [ -x "$EXECBIT_SCRIPT" ]; then
  fail=$((fail + 1))
  failures+=("execute-bit test setup -- chmod -x did not remove the execute bit on this filesystem")
  echo "FAIL: execute-bit test setup -- chmod -x did not remove the execute bit on this filesystem; the case below would be meaningless, skipping it"
else
  pass=$((pass + 1))
  echo "PASS: execute-bit test setup confirms the scratch copy is genuinely non-executable"

  # Contrast case, not a claim about current hooks.json behaviour: direct
  # invocation of a non-executable file fails with a permission error. This
  # is the exact failure this repo's own runtime treats as a silent ALLOW
  # (hook execution failures are non-blocking, per SECURITY.md) -- no
  # hooks.json entry here invokes a script this way; this only demonstrates
  # the failure mode the bash-wrapper fix actually addresses.
  direct_out=$("$EXECBIT_SCRIPT" <<<'{}' 2>&1)
  direct_status=$?
  if [ "$direct_status" -ne 0 ] && echo "$direct_out" | grep -qi "permission denied"; then
    pass=$((pass + 1))
    echo "PASS: direct invocation of the non-executable copy fails with a permission error, confirming the failure mode PILOT-3's fix actually addresses"
  else
    fail=$((fail + 1))
    failures+=("execute-bit contrast case (expected a permission-denied failure on direct invocation, got status=$direct_status: $direct_out)")
    echo "FAIL: direct invocation of the non-executable copy did not fail as expected (status=$direct_status, output=$direct_out)"
  fi

  # The actual fix, and the case that matters: invoked the way every
  # hooks.json entry in this repo actually invokes a script -- via
  # `bash <script>` -- the gate still runs and still denies a genuine
  # true-positive case, execute bit or no execute bit.
  run_case_abspath "gate-plan-exists: execute bit stripped, invoked via bash (PILOT-3 fix) -> still denies" \
    "$EXECBIT_SCRIPT" \
    "$(json_path /repo/src/a.py)" deny "$EMPTY"
fi

echo
echo "==================================="
echo "$pass passed, $fail failed"
if [ "$fail" -gt 0 ]; then
  printf 'FAILED: %s\n' "${failures[@]}"
  exit 1
fi
exit 0
