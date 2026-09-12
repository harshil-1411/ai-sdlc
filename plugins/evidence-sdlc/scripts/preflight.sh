#!/bin/bash
# Verifies the environment every other gate script in this framework depends on.
# Must report loudly even when the tool the OTHER gates rely on (jq) is itself
# missing — that is exactly the fail-open condition this script exists to catch.
cat >/dev/null

plugin_root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
plugins_dir="$(cd "$plugin_root/.." && pwd 2>/dev/null)"
[ -z "$plugins_dir" ] && plugins_dir="$plugin_root/.."

failures=()

have_jq=1
if ! command -v jq >/dev/null 2>&1; then
  have_jq=0
  failures+=("jq is not resolvable on PATH — every gate script shells out to jq to read tool input and emit its decision; without it, gates cannot run at all")
fi

unreadable=""
while IFS= read -r f; do
  [ -n "$f" ] || continue
  if [ ! -r "$f" ]; then
    unreadable="${unreadable}${unreadable:+, }${f}"
  fi
done < <(find "$plugins_dir" -type f -name '*.sh' -path '*/scripts/*' 2>/dev/null)

if [ -n "$unreadable" ]; then
  failures+=("unreadable gate script(s), so they cannot execute: ${unreadable}")
fi

profile_note="Repository profile found at .evidence/context/stack.md."
if [ ! -f ".evidence/context/stack.md" ]; then
  profile_note="No repository profile at .evidence/context/stack.md (informational only, not a preflight failure)."
fi

if [ "${#failures[@]}" -gt 0 ]; then
  joined=$(printf '%s; ' "${failures[@]}")
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
  escaped=$(printf '%s' "$message" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' ' ')
  printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "SessionStart",\n    "additionalContext": "%s"\n  }\n}\n' "$escaped"
fi
