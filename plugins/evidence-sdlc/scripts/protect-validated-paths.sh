#!/bin/bash
# Paths under formal change control. Editing these needs a change ticket in the
# environment (CHANGE_TICKET) so the edit is attributable in the change record.
input=$(cat)
path=$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<<"$input")
[ -z "$path" ] && exit 0

protected=0
case "$path" in
  *migrations/*|*infra/*|*terraform/*|*/audit/*|*/signing/*|*/crypto/*|*validation/*) protected=1 ;;
esac
[ "$protected" -eq 0 ] && exit 0

if [ -n "$CHANGE_TICKET" ]; then
  jq -n --arg p "$path" --arg t "$CHANGE_TICKET" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      additionalContext: ("Editing change-controlled path " + $p + " under ticket " + $t + ". The change record must reference this ticket and the compliance-reviewer agent must run before this PR is opened.")
    }
  }'
  exit 0
fi

jq -n --arg p "$path" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: ($p + " is under formal change control (migrations, infrastructure, audit trail, signing, crypto, or validation assets). Set CHANGE_TICKET to an approved change record before editing, or route this through the change board.")
  }
}'
