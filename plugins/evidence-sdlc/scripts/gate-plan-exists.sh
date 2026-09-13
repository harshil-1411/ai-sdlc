#!/bin/bash
# Nothing in a source directory gets edited without an approved plan.md on disk.
# Docs, the artifact chain itself, and scratch files are exempt.
input=$(cat)

# Fail closed, not open, if jq itself is unavailable -- without it this script
# cannot read the tool call at all, and falling through to exit 0 would allow
# every source edit unconditionally. See SECURITY.md.
if ! command -v jq >/dev/null 2>&1; then
  msg="gate-plan-exists could not evaluate this tool call because 'jq' is not available on PATH. Failing closed rather than silently allowing an unenforced change. Install jq and retry -- see SECURITY.md."
  escaped="${msg//\\/\\\\}"
  escaped="${escaped//\"/\\\"}"
  printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "PreToolUse",\n    "permissionDecision": "deny",\n    "permissionDecisionReason": "%s"\n  }\n}\n' "$escaped"
  exit 0
fi

path=$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<<"$input")
[ -z "$path" ] && exit 0

case "$path" in
  */intent/*|*/docs/*|*intent.md|*spec.md|*plan.md|plan/*.md|*CLAUDE.md|*.claude/*|*/validation/*|*/tmp/*|*.log) exit 0 ;;
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
#
# plan/<TRACKER-KEY>.md is the namespaced form for concurrent sessions in
# separate worktrees (see codebase-grounded-planning's "Concurrent sessions"
# section): each session's plan lives under its own tracker key instead of
# every session fighting over one bare plan.md. The key must match a tracker
# key found in the CURRENT branch name, so one session cannot satisfy this
# gate by pointing at a plan that claims a different piece of work. Bare
# plan.md (and the two locations above) keep working unchanged.
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
key_pattern="${EVIDENCE_ISSUE_KEY_PATTERN:-[A-Z][A-Z0-9]+-[0-9]+}"
branch_key=$(echo "$branch" | grep -Eo "$key_pattern" | head -1)

if [ -f plan.md ] || ls */plan.md >/dev/null 2>&1 || ls intent/*/plan.md >/dev/null 2>&1 \
   || { [ -n "$branch_key" ] && [ -f "plan/$branch_key.md" ]; }; then
  exit 0
fi

jq -n '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: "No plan.md found (checked plan.md, */plan.md, intent/*/plan.md, and plan/<tracker-key>.md for the current branch). Run the codebase-grounded-planning skill in plan mode and commit an approved plan before editing source. See the Evidence Chain handbook."
  }
}'
