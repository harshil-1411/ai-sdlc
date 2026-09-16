#!/bin/bash
# Local, append-only trace of what the agent changed. This is a convenience record
# for engineers; the OpenTelemetry export and git history remain the systems of record.
# Sharded one file per session (agent-edits-<session-id>.tsv), not one shared file --
# concurrent sessions or worktrees each append only to their own shard, so two
# sessions writing at the same moment never interleave or corrupt one file. A
# reader wanting the full picture globs .claude/logs/agent-edits-*.tsv and merges
# by timestamp.
input=$(cat)
mkdir -p .claude/logs
path=$(jq -r '.tool_input.file_path // .tool_input.path // "unknown"' <<<"$input")
sid=$(jq -r '.session_id // "unknown"' <<<"$input")
safe_sid=$(printf '%s' "$sid" | tr -c 'A-Za-z0-9_-' '_')
[ -z "$safe_sid" ] && safe_sid="unknown"
printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$sid" "${USER:-unknown}" "$path" >> ".claude/logs/agent-edits-${safe_sid}.tsv"
exit 0
