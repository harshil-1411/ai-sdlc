#!/bin/bash
# Tell the session what mode it is in, so it does not have to guess.
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
plan="none"
p=$(ls plan.md */plan.md intent/*/plan.md 2>/dev/null | head -1)
[ -n "$p" ] && plan="$p"

# Same namespaced-plan lookup gate-plan-exists.sh uses: a plan/<TRACKER-KEY>.md
# satisfies the gate when the key is present in the current branch name, even
# though none of the three globs above match it. Without this, a concurrent
# session using only a keyed plan file is correctly allowed to edit by the gate
# but told "Approved plan on disk: none" here -- a cosmetic but confusing
# mismatch between what is reported and what is actually enforced.
if [ "$plan" = "none" ]; then
  key_pattern="${EVIDENCE_ISSUE_KEY_PATTERN:-[A-Z][A-Z0-9]+-[0-9]+}"
  branch_key=$(echo "$branch" | grep -Eo "$key_pattern" | head -1)
  if [ -n "$branch_key" ] && [ -f "plan/$branch_key.md" ]; then
    plan="plan/$branch_key.md"
  fi
fi

jq -n --arg b "$branch" --arg p "$plan" --arg t "${CHANGE_TICKET:-none}" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: ("Evidence Chain session. Branch: " + $b + ". Approved plan on disk: " + $p + ". Change ticket in environment: " + $t + ". Source edits are gated on an approved plan.md; migrations, infrastructure, audit, signing, crypto and validation paths are gated on a change ticket; production deploys are gated on a release authorization.")
  }
}'
