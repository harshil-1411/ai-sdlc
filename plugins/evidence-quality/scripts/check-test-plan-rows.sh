#!/bin/bash
# Warn (do not block) when a plan.md has requirement IDs with no test row.
# Advisory by design: blocking here would fire mid-thought during planning.
plan=$(ls plan.md */plan.md intent/*/plan.md 2>/dev/null | head -1)
[ -z "$plan" ] && exit 0

reqs=$(grep -oE 'REQ-[A-Za-z0-9]+-[0-9]+' "$plan" 2>/dev/null | sort -u)
[ -z "$reqs" ] && exit 0

missing=""
while read -r r; do
  [ -z "$r" ] && continue
  # a requirement is "covered" if it appears on a line that also names a test
  if ! grep -E "$r" "$plan" | grep -qiE 'test|case|spec|C[0-9]+'; then
    missing="$missing $r"
  fi
done <<< "$reqs"

[ -z "$missing" ] && exit 0

jq -n --arg m "$missing" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: ("The plan has requirement IDs with no named test:" + $m + ". A requirement with no test is an incomplete plan. Apply the test-strategy skill and add rows before implementation is reported complete.")
  }
}'
