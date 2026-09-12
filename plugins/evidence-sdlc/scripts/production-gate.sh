#!/bin/bash
# The agent may act up to the production gate and not past it.
input=$(cat)
cmd=$(jq -r '.tool_input.command // empty' <<<"$input")
[ -z "$cmd" ] && exit 0

# Match "prod"/"production" as a whole token (bounded by non-letters or string
# edges), not as a substring. The previous `case "$cmd" in *prod*|*production*)`
# glob matched any word merely containing "prod" -- "reproduce", "product",
# "reproducible", "byproduct" -- false-triggering this gate on ordinary commands
# and commit messages that had nothing to do with a production deploy.
if [[ ! "$cmd" =~ (^|[^A-Za-z])(prod|production)([^A-Za-z]|$) ]]; then
  exit 0
fi

if [ -n "$RELEASE_APPROVAL" ]; then
  exit 0
fi

echo "Production deploys require a named release authorization. Set RELEASE_APPROVAL to the release manager's approval reference. The validation package for this release must be signed off by QA/RA first." >&2
exit 2
