#!/bin/bash
# Thin launcher for the Python gate engine. Fails closed on PreToolUse if python3
# is missing, because without it no gate can evaluate anything.
event="${1:-pre}"
here="${BASH_SOURCE[0]%/*}"
py="${EVIDENCE_PYTHON:-python3}"
if ! command -v "$py" >/dev/null 2>&1; then
  cat >/dev/null
  if [ "$event" = "pre" ]; then
    printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"The Evidence Chain gate engine needs python3 on PATH and cannot find it, so no gate can run. Failing closed. Install Python 3.8+ (or set EVIDENCE_PYTHON) and restart the session."}}'
  elif [ "$event" = "session-start" ]; then
    printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"EVIDENCE CHAIN GATES NOT RUNNING: python3 is not on PATH. Every file change and command will be denied until it is installed."}}'
  fi
  exit 0
fi
exec "$py" "$here/hook.py" "$event"
