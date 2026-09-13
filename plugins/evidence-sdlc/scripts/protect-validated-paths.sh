#!/bin/bash
# Paths under formal change control. Editing these needs a change ticket in the
# environment (CHANGE_TICKET) so the edit is attributable in the change record.
input=$(cat)

# Fail closed, not open, if jq itself is unavailable -- without it this script
# cannot read the tool call at all, and falling through to exit 0 would allow
# an edit to a change-controlled path unconditionally. See SECURITY.md.
if ! command -v jq >/dev/null 2>&1; then
  msg="protect-validated-paths could not evaluate this tool call because 'jq' is not available on PATH. Failing closed rather than silently allowing an unenforced change. Install jq and retry -- see SECURITY.md."
  escaped="${msg//\\/\\\\}"
  escaped="${escaped//\"/\\\"}"
  printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "PreToolUse",\n    "permissionDecision": "deny",\n    "permissionDecisionReason": "%s"\n  }\n}\n' "$escaped"
  exit 0
fi

path=$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<<"$input")
[ -z "$path" ] && exit 0

# Match exact path segments, not substrings. The previous globs required no
# leading boundary on migrations/infra/terraform/validation, so an unrelated
# directory whose name merely ENDS in one of those words also matched --
# "cache-invalidation/" (contains "validation/"), "test-infra/" (contains
# "infra/") -- wrongly pulling ordinary code under change control. The
# */audit/*, */signing/*, */crypto/* patterns had the opposite gap: requiring
# a leading slash meant a root-level "audit/report.pdf" (no leading slash)
# was missed while "src/audit/report.pdf" was caught.
protected=0
IFS='/' read -ra parts <<< "$path"
for seg in "${parts[@]}"; do
  case "$seg" in
    migrations|infra|terraform|audit|signing|crypto|validation) protected=1; break ;;
  esac
done
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
