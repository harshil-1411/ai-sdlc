#!/bin/bash
# An agent fixing code must not be able to weaken the check on that code.
# Set FIX_TASK=1 for bug-fix sessions where the failing test is written first.
input=$(cat)
path=$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<<"$input")
[ -z "$path" ] && exit 0
[ "${FIX_TASK:-0}" != "1" ] && exit 0

case "$path" in
  *test_*|*_test.*|*.test.*|*.spec.*|*/tests/*|*/__tests__/*|*/qa/*) ;;
  *) exit 0 ;;
esac

jq -n '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: "This is a fix task (FIX_TASK=1). The failing test was committed first and proves the bug. Fix the code, not the test. If the test itself is genuinely wrong, stop and say so — a human decides that."
  }
}'
