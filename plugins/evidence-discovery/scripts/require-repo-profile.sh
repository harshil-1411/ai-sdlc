#!/bin/bash
# Sessions should know what stack they are in. Missing or incomplete profile is
# surfaced as context, and blocks source edits only when an [ASK] is unresolved.
input=$(cat)
profile=".evidence/context/stack.md"

if [ ! -f "$profile" ]; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: "No repository profile exists at .evidence/context/stack.md. The technology stack, deployment stack, toolchain and design system for this repository have not been established. Run stack-discovery, toolchain-discovery and design-system-discovery before planning any change. Do not assume a framework, runtime, datastore or deployment target."
    }
  }'
  exit 0
fi

asks=$(grep -c '\[ASK\]' .evidence/context/*.md 2>/dev/null | awk -F: '{s+=$2} END {print s+0}')
jq -n --arg a "$asks" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: ("Repository profile present at .evidence/context/. Read stack.md, deployment.md, toolchain.md and design-system.md before planning. Unresolved [ASK] items: " + $a + ". An [ASK] in an area this change depends on is a blocker — ask the human rather than assuming.")
  }
}'
