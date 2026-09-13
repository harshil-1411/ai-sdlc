#!/bin/bash
# The agent may act up to the production gate and not past it.
input=$(cat)

# Fail closed, not open, if jq itself is unavailable -- without it this script
# cannot tell whether the command is a production deploy at all, and falling
# through to exit 0 would allow an unverified deploy command through
# unconditionally. See SECURITY.md.
if ! command -v jq >/dev/null 2>&1; then
  echo "production-gate could not evaluate this tool call because 'jq' is not available on PATH. Failing closed rather than silently allowing an unverified deploy command through. Install jq and retry -- see SECURITY.md." >&2
  exit 2
fi

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
