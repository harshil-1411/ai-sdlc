#!/bin/bash
# Verifies the environment every other gate script in this framework depends on.
# Must report loudly even when PATH is so stripped that the usual coreutils
# (cat, dirname, sed, tr, find) aren't resolvable either -- that is the same class
# of environment where a gate silently fails open, so this uses bash builtins
# only and must never itself fail silently.
shopt -s nullglob globstar

while IFS= read -r _; do :; done

plugin_root="${CLAUDE_PLUGIN_ROOT:-${BASH_SOURCE[0]%/*}/..}"
plugins_dir="${plugin_root}/.."

failures=()

have_jq=1
if ! command -v jq >/dev/null 2>&1; then
  have_jq=0
  failures+=("jq is not resolvable on PATH -- every gate script shells out to jq to read tool input and emit its decision; without it, gates cannot run at all")
fi

unreadable=""
for f in "$plugins_dir"/*/scripts/*.sh; do
  [ -e "$f" ] || continue
  if [ ! -r "$f" ]; then
    unreadable="${unreadable}${unreadable:+, }${f}"
  fi
done

if [ -n "$unreadable" ]; then
  failures+=("unreadable gate script(s), so they cannot execute: ${unreadable}")
fi

profile_note="Repository profile found at .evidence/context/stack.md."
if [ ! -f ".evidence/context/stack.md" ]; then
  profile_note="No repository profile at .evidence/context/stack.md (informational only, not a preflight failure)."
fi

if [ "${#failures[@]}" -gt 0 ]; then
  joined=""
  for msg in "${failures[@]}"; do
    joined="${joined}${msg}; "
  done
  message="PREFLIGHT FAILED: ${joined}Gates may not be enforcing. Do not make source changes until this is fixed. ${profile_note}"
else
  message="Preflight OK: jq resolves on PATH and all gate scripts are readable. ${profile_note}"
fi

if [ "$have_jq" -eq 1 ]; then
  jq -n --arg m "$message" '{
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: $m
    }
  }'
else
  escaped="${message//\\/\\\\}"
  escaped="${escaped//\"/\\\"}"
  escaped="${escaped//$'\n'/ }"
  printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "SessionStart",\n    "additionalContext": "%s"\n  }\n}\n' "$escaped"
fi
