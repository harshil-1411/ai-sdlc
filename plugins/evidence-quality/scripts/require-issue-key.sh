#!/bin/bash
# No commit without the tracker key. The key pattern comes from the repository
# profile, not from this script — set EVIDENCE_ISSUE_KEY_PATTERN in project settings
# or .evidence/context/toolchain.md. Default is a conservative generic pattern.
input=$(cat)
cmd=$(jq -r '.tool_input.command // empty' <<<"$input")
[ -z "$cmd" ] && exit 0

case "$cmd" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac

pattern="${EVIDENCE_ISSUE_KEY_PATTERN:-[A-Z][A-Z0-9]+-[0-9]+}"

# The key may be in the commit message or already in the branch name.
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if echo "$cmd" | grep -Eq "$pattern"; then exit 0; fi
if echo "$branch" | grep -Eq "$pattern"; then exit 0; fi

jq -n --arg p "$pattern" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: ("No tracker issue key found in the commit message or the branch name. Every commit must carry the key (pattern: " + $p + ") so the traceability chain from requirement to test to evidence holds. If no issue exists for this work, create one first — do not add the key retrospectively.")
  }
}'
