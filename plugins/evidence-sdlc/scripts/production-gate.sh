#!/bin/bash
# The agent may act up to the production gate and not past it.
input=$(cat)
cmd=$(jq -r '.tool_input.command // empty' <<<"$input")
[ -z "$cmd" ] && exit 0

case "$cmd" in
  *prod*|*production*) ;;
  *) exit 0 ;;
esac

if [ -n "$RELEASE_APPROVAL" ]; then
  exit 0
fi

echo "Production deploys require a named release authorization. Set RELEASE_APPROVAL to the release manager's approval reference. The validation package for this release must be signed off by QA/RA first." >&2
exit 2
