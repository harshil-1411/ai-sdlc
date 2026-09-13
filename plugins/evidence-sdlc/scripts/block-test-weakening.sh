#!/bin/bash
# An agent fixing code must not be able to weaken the check on that code.
# Set FIX_TASK=1 for bug-fix sessions where the failing test is written first.
input=$(cat)
[ "${FIX_TASK:-0}" != "1" ] && exit 0

# Fail closed, not open, if jq itself is unavailable. Reordered ahead of the
# jq-based path extraction below: this gate is only ever consequential during
# a fix task (FIX_TASK=1, checked above without needing jq), so failing closed
# on a missing jq only when it would actually have mattered avoids denying
# every ordinary edit outside a fix task. See SECURITY.md.
if ! command -v jq >/dev/null 2>&1; then
  msg="block-test-weakening could not evaluate this tool call because 'jq' is not available on PATH. Failing closed rather than silently allowing the test to be weakened during a fix task. Install jq and retry -- see SECURITY.md."
  escaped="${msg//\\/\\\\}"
  escaped="${escaped//\"/\\\"}"
  printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "PreToolUse",\n    "permissionDecision": "deny",\n    "permissionDecisionReason": "%s"\n  }\n}\n' "$escaped"
  exit 0
fi

path=$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<<"$input")
[ -z "$path" ] && exit 0

# Test-file patterns are checked against the basename, and *test_* must be a
# PREFIX of it (not merely present anywhere in the path). The previous
# `*test_*` glob matched any path containing that substring, which includes
# ordinary non-test files like "latest_migration.py" or "fastest_path.py"
# (both contain "test_" as a substring of "latest_"/"fastest_") -- falsely
# denying edits to them during a fix task.
#
# Directory names are checked as exact path segments, not substrings, and
# without requiring a leading slash -- the previous `*/tests/*` glob also
# missed a root-level "tests/helpers.py" (no leading slash) while still
# catching "src/tests/helpers.py", an inconsistency with the same root cause.
base="${path##*/}"
protected=0

case "$base" in
  test_*|*_test.*|*.test.*|*.spec.*) protected=1 ;;
esac

if [ "$protected" -eq 0 ]; then
  IFS='/' read -ra parts <<< "$path"
  for seg in "${parts[@]}"; do
    case "$seg" in
      tests|__tests__|qa) protected=1; break ;;
    esac
  done
fi

[ "$protected" -eq 0 ] && exit 0

jq -n '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: "This is a fix task (FIX_TASK=1). The failing test was committed first and proves the bug. Fix the code, not the test. If the test itself is genuinely wrong, stop and say so — a human decides that."
  }
}'
