#!/bin/bash
# Tell the session what mode it is in, so it does not have to guess.
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
plan="none"
p=$(ls plan.md */plan.md intent/*/plan.md 2>/dev/null | head -1)
[ -n "$p" ] && plan="$p"

jq -n --arg b "$branch" --arg p "$plan" --arg t "${CHANGE_TICKET:-none}" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: ("Evidence Chain session. Branch: " + $b + ". Approved plan on disk: " + $p + ". Change ticket in environment: " + $t + ". Source edits are gated on an approved plan.md; migrations, infrastructure, audit, signing, crypto and validation paths are gated on a change ticket; production deploys are gated on a release authorization.")
  }
}'
