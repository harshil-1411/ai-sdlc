#!/bin/bash
# Advisory-only sensor, not a gate: this NEVER denies a tool call. It checks
# whether a just-written spec.md's "Areas of concern" section, or a plan.md's
# "Files claimed" section, is missing or still the raw template placeholder --
# operationalizing spec-and-design's own rule ("Areas of concern... this
# section being empty is suspicious -- say so if it is") and
# codebase-grounded-planning's "Files claimed" requirement, neither of which
# anything actually checked before this. If it cannot run for any reason (no
# jq, unreadable file, path doesn't match, heading not found), it degrades to
# complete silence and exit 0 -- there is nothing to protect here, unlike the
# six real gates, so this deliberately does NOT fail closed on a missing jq.
input=$(cat)

command -v jq >/dev/null 2>&1 || exit 0
path=$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<<"$input" 2>/dev/null)
[ -z "$path" ] && exit 0

base="${path##*/}"
section=""
case "$base" in
  spec.md) section="Areas of concern" ;;
  # plan.md, and the namespaced plan/<TRACKER-KEY>.md form for concurrent
  # sessions (see gate-plan-exists.sh) -- basename alone won't catch the
  # namespaced form since it's "<KEY>.md", not "plan.md", so also check
  # whether the immediate parent directory is literally "plan".
  plan.md) section="Files claimed" ;;
  *)
    parent_dir="${path%/*}"
    parent_base="${parent_dir##*/}"
    if [ "$parent_base" = "plan" ] && [[ "$base" == *.md ]]; then
      section="Files claimed"
    else
      exit 0
    fi
    ;;
esac

[ -f "$path" ] || exit 0

# Extract the body between "## <section>" and the next "## " heading (or EOF).
body=$(awk -v h="## $section" '
  $0 == h { found=1; next }
  found && /^## / { found=0 }
  found { print }
' "$path")

# Collapse to one line, trim outer whitespace, so a multi-line placeholder or
# multi-line real content both compare cleanly.
trimmed=$(printf '%s' "$body" | tr '\n' ' ' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/[[:space:]][[:space:]]*/ /g')

is_stub=0
if [ -z "$trimmed" ]; then
  is_stub=1
elif [[ "$trimmed" == "<"*">" ]]; then
  is_stub=1
fi

[ "$is_stub" -eq 0 ] && exit 0

case "$section" in
  "Areas of concern")
    rule_ref='spec-and-design'"'"'s own rule that this section being empty is suspicious and should say so if it is' ;;
  "Files claimed")
    rule_ref='codebase-grounded-planning'"'"'s "Concurrent sessions" requirement that every path a plan touches is claimed before work starts' ;;
esac

msg="${path}'s \"## ${section}\" section is missing or still looks like the unfilled template placeholder. This operationalizes ${rule_ref}. Advisory only -- nothing was blocked."

jq -n --arg m "$msg" '{
  hookSpecificOutput: {
    hookEventName: "PostToolUse",
    additionalContext: $m
  }
}'
