#!/bin/bash
# Nothing in a source directory gets edited without an approved plan.md on disk.
# Docs, the artifact chain itself, and scratch files are exempt.
input=$(cat)
path=$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<<"$input")
[ -z "$path" ] && exit 0

case "$path" in
  */intent/*|*/docs/*|*intent.md|*spec.md|*plan.md|*CLAUDE.md|*.claude/*|*/validation/*|*/tmp/*|*.log) exit 0 ;;
esac

# Gate source paths. The pattern is repo-specific and comes from the repository
# profile, not from this script. Set EVIDENCE_SOURCE_GLOB in project settings; the
# default is a broad "anything that is not obviously not source" rule.
src_pattern="${EVIDENCE_SOURCE_GLOB:-}"
if [ -n "$src_pattern" ]; then
  case "$path" in
    $src_pattern) ;;
    *) exit 0 ;;
  esac
else
  # No profile-derived pattern configured: gate anything that looks like code.
  case "$path" in
    *.md|*.txt|*.json|*.yaml|*.yml|*.csv|*.lock) exit 0 ;;
  esac
fi

# Each location is an independent alternative (OR), not a simultaneous
# requirement. `ls plan.md */plan.md intent/*/plan.md` used to fail (and thus
# deny) whenever ANY one of the three glob patterns had no match, even when
# plan.md existed at the repo root -- because bash passes an unmatched glob to
# ls as a literal, nonexistent filename, and ls's exit status reflects that.
if [ -f plan.md ] || ls */plan.md >/dev/null 2>&1 || ls intent/*/plan.md >/dev/null 2>&1; then
  exit 0
fi

jq -n '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: "No plan.md found. Run the codebase-grounded-planning skill in plan mode and commit an approved plan before editing source. See the Evidence Chain handbook."
  }
}'
