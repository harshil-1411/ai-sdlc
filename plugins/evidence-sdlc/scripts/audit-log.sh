#!/bin/bash
# Local, append-only trace of what the agent changed. This is a convenience record
# for engineers; the OpenTelemetry export and git history remain the systems of record.
input=$(cat)
mkdir -p .claude/logs
path=$(jq -r '.tool_input.file_path // .tool_input.path // "unknown"' <<<"$input")
sid=$(jq -r '.session_id // "unknown"' <<<"$input")
printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$sid" "${USER:-unknown}" "$path" >> .claude/logs/agent-edits.tsv
exit 0
