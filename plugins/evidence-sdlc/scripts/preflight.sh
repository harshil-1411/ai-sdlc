#!/bin/bash
# Verifies the environment the gate engine depends on, loudly. Uses bash builtins
# only, so it still reports when PATH is stripped -- the same class of environment
# in which a gate would otherwise silently fail to run.
shopt -s nullglob

while IFS= read -r _; do :; done

plugin_root="${CLAUDE_PLUGIN_ROOT:-${BASH_SOURCE[0]%/*}/..}"
engine="${plugin_root}/scripts/engine"
py="${EVIDENCE_PYTHON:-python3}"
failures=()

if ! command -v "$py" >/dev/null 2>&1; then
  failures+=("python3 is not on PATH -- the gate engine cannot run, so every file change and command will be denied")
else
  ver=$("$py" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)
  case "$ver" in
    3.[0-7]|2.*|"") failures+=("python ${ver:-unknown} is too old for the gate engine (needs 3.8+)") ;;
  esac
fi

for f in hook.py hook.sh evidence_policy.py cmdparse.py state.py secretscan.py lifecycle.py sensor.py; do
  [ -r "$engine/$f" ] || failures+=("gate engine file missing or unreadable: $engine/$f")
done
[ -r "${plugin_root}/policy/default-policy.json" ] || failures+=("default policy missing: ${plugin_root}/policy/default-policy.json")

profile_note="Repository profile found at .evidence/context/stack.md."
[ -f ".evidence/context/stack.md" ] || profile_note="No repository profile at .evidence/context/stack.md (run stack-discovery; informational)."

if [ "${#failures[@]}" -gt 0 ]; then
  joined=""
  for m in "${failures[@]}"; do joined="${joined}${m}; "; done
  message="PREFLIGHT FAILED: ${joined}The gates fail closed until this is fixed. ${profile_note}"
else
  message="Preflight OK: python ${ver} and the gate engine are in place. ${profile_note}"
fi

escaped="${message//\\/\\\\}"
escaped="${escaped//\"/\\\"}"
escaped="${escaped//$'\n'/ }"
printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "SessionStart",\n    "additionalContext": "%s"\n  }\n}\n' "$escaped"
