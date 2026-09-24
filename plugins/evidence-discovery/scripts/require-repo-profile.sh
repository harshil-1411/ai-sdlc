#!/bin/bash
# Sessions should know what stack they are in. A missing or incomplete profile is
# surfaced as context only: this hook never blocks anything. Enforcement lives in the
# evidence-sdlc gate engine. Bash builtins plus grep only -- no jq.
while IFS= read -r _; do :; done
profile=".evidence/context/stack.md"

emit() {
  local m="$1"
  m="${m//\\/\\\\}"
  m="${m//\"/\\\"}"
  printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "SessionStart",\n    "additionalContext": "%s"\n  }\n}\n' "$m"
}

if [ ! -f "$profile" ]; then
  emit "No repository profile exists at .evidence/context/stack.md. The technology stack, deployment stack, toolchain and design system for this repository have not been established. Run stack-discovery, toolchain-discovery and design-system-discovery before planning any change, and test-strategy-discovery before the first test plan. Do not assume a framework, runtime, datastore or deployment target."
  exit 0
fi

asks=0
for f in .evidence/context/*.md; do
  [ -f "$f" ] || continue
  n=$(grep -c '\[ASK\]' "$f" 2>/dev/null || true)
  asks=$((asks + ${n:-0}))
done
emit "Repository profile present at .evidence/context/. Read stack.md, deployment.md, toolchain.md and design-system.md before planning, and test-strategy.md before any test plan (if it is absent, run test-strategy-discovery). Unresolved [ASK] items: ${asks}. An [ASK] in an area this change depends on is a blocker — ask the human rather than assuming."
