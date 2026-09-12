#!/bin/bash
# No commit without the tracker key. The key pattern comes from the repository
# profile, not from this script — set EVIDENCE_ISSUE_KEY_PATTERN in project settings
# or .evidence/context/toolchain.md. Default is a conservative generic pattern.
input=$(cat)
cmd=$(jq -r '.tool_input.command // empty' <<<"$input")
[ -z "$cmd" ] && exit 0

# Require "git commit" at a command-invocation position (start of a line, or
# right after a shell chaining operator), not merely present as text anywhere
# in the command. The previous substring check matched a command that only
# MENTIONED "git commit" inside a quoted string or heredoc body -- e.g.
# `echo "remember to git commit later"`, or test payload data constructing a
# sample command string -- denying it as though it were a real, un-keyed
# commit. This was hit live: a heredoc writing a test script whose sample
# data contained the literal text "git commit -m '...'" was denied even
# though no commit was being made.
if ! printf '%s\n' "$cmd" | grep -Eq '(^|[;&|`(])[[:space:]]*git[[:space:]]+commit([[:space:]]|$)'; then
  exit 0
fi

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
