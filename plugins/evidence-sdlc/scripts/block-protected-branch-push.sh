#!/bin/bash
# Segregation of duties: the agent has no route to main. Branch protection is the
# real control; this stops the attempt earlier and explains why.
input=$(cat)
cmd=$(jq -r '.tool_input.command // empty' <<<"$input")
[ -z "$cmd" ] && exit 0

# Require "git push" at a command-invocation position (start of a line, or
# right after a shell chaining operator), not merely present as text anywhere
# in the command -- the same class of false positive found and fixed in
# require-issue-key.sh's "git commit" check. The previous substring check
# denied a plain `echo "remember to git push after review"` while sitting on
# a protected branch, even though it does not push anything.
if ! printf '%s\n' "$cmd" | grep -Eq '(^|[;&|`(])[[:space:]]*git[[:space:]]+push([[:space:]]|$)'; then
  exit 0
fi

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
case "$branch" in
  main|master|release|release/*|hotfix/*) ;;
  *) exit 0 ;;
esac

jq -n --arg b "$branch" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: ("Direct push to " + $b + " is not available to an agent session. Open a pull request; a human code owner approves. The agent that wrote the change has no route to approve it. This is a segregation-of-duties control, not a preference.")
  }
}'
