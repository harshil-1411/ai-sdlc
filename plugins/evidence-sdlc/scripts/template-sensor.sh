#!/bin/bash
# Advisory-only sensor, not a gate: this NEVER denies a tool call. It checks:
# - a just-written spec.md's "Areas of concern" section, or a plan.md's
#   "Files claimed" section, for being missing or still the raw template
#   placeholder -- operationalizing spec-and-design's own rule ("Areas of
#   concern... this section being empty is suspicious -- say so if it is")
#   and codebase-grounded-planning's "Files claimed" requirement.
# - a Tier 2/3 plan.md (per a sibling spec.md's "Risk tier:" line) whose
#   "Order of work" names no CHECKPOINT step -- operationalizing
#   codebase-grounded-planning's mid-flight checkpoint requirement.
# - a new SKILL.md with no eval case yet under its plugin's evals/ directory
#   -- operationalizing definition-of-ready-and-done.md's "Eval case added
#   under evals/" row.
# None of this was checked before this script existed. If it cannot run for
# any reason (no jq, unreadable file, path doesn't match, heading not found),
# it degrades to complete silence and exit 0 -- there is nothing to protect
# here, unlike the six real gates, so this deliberately does NOT fail closed
# on a missing jq.
input=$(cat)

command -v jq >/dev/null 2>&1 || exit 0
path=$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<<"$input" 2>/dev/null)
[ -z "$path" ] && exit 0
[ -f "$path" ] || exit 0

base="${path##*/}"
parent_dir="${path%/*}"
parent_base="${parent_dir##*/}"

# plan.md, and the namespaced plan/<TRACKER-KEY>.md form for concurrent
# sessions (see gate-plan-exists.sh) -- basename alone won't catch the
# namespaced form since it's "<KEY>.md", not "plan.md", so also check
# whether the immediate parent directory is literally "plan".
is_plan=0
case "$base" in
  plan.md) is_plan=1 ;;
  *.md) [ "$parent_base" = "plan" ] && is_plan=1 ;;
esac

# Extract the body between "## <heading>" and the next "## " heading (or EOF).
extract_section() {
  awk -v h="## $2" '
    $0 == h { found=1; next }
    found && /^## / { found=0 }
    found { print }
  ' "$1"
}

# Collapse to one line, trim outer whitespace, so a multi-line placeholder or
# multi-line real content both compare cleanly. True (0) if stub/empty.
is_stub_body() {
  local trimmed
  trimmed=$(printf '%s' "$1" | tr '\n' ' ' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/[[:space:]][[:space:]]*/ /g')
  [ -z "$trimmed" ] && return 0
  [[ "$trimmed" == "<"*">" ]] && return 0
  return 1
}

messages=()

if [ "$base" = "spec.md" ]; then
  body=$(extract_section "$path" "Areas of concern")
  if is_stub_body "$body"; then
    messages+=("${path}'s \"## Areas of concern\" section is missing or still looks like the unfilled template placeholder. This operationalizes spec-and-design's own rule that this section being empty is suspicious and should say so if it is. Advisory only -- nothing was blocked.")
  fi

elif [ "$is_plan" -eq 1 ]; then
  body=$(extract_section "$path" "Files claimed")
  if is_stub_body "$body"; then
    messages+=("${path}'s \"## Files claimed\" section is missing or still looks like the unfilled template placeholder. This operationalizes codebase-grounded-planning's \"Concurrent sessions\" requirement that every path a plan touches is claimed before work starts. Advisory only -- nothing was blocked.")
  fi

  # Mid-flight checkpoint: only meaningful when a sibling spec.md in the same
  # directory states Tier 2/3. No sibling, or Tier 1, degrades to silence --
  # this is a heuristic pairing, not a guarantee (see plan.md's own "Risks").
  spec_sibling="$parent_dir/spec.md"
  if [ -f "$spec_sibling" ] && grep -Eq 'Risk tier: *[23]\b' "$spec_sibling"; then
    order_body=$(extract_section "$path" "Order of work")
    if ! printf '%s' "$order_body" | grep -qi 'CHECKPOINT'; then
      messages+=("${path} is Tier 2/3 (per ${spec_sibling}) but its \"## Order of work\" section names no CHECKPOINT step. This operationalizes codebase-grounded-planning's mid-flight checkpoint requirement for long Tier 2/3 work. Advisory only -- nothing was blocked.")
    fi
  fi

elif [ "$base" = "SKILL.md" ]; then
  case "$path" in
    plugins/*/skills/*/SKILL.md|*/plugins/*/skills/*/SKILL.md) ;;
    *) exit 0 ;;
  esac
  plugin_root="${path%/skills/*}"
  skill_name="$parent_base"
  evals_dir="$plugin_root/evals"
  has_case=0
  if [ -d "$evals_dir" ]; then
    for d in "$evals_dir/${skill_name}"-*; do
      [ -d "$d" ] && { has_case=1; break; }
    done
  fi
  if [ "$has_case" -eq 0 ]; then
    messages+=("${path} is a new skill with no eval case found under ${evals_dir}/ matching \"${skill_name}-*\". This operationalizes definition-of-ready-and-done.md's \"Eval case added under evals/\" row. Advisory only -- nothing was blocked.")
  fi

else
  exit 0
fi

[ "${#messages[@]}" -eq 0 ] && exit 0

joined=$(printf '%s\n\n' "${messages[@]}")
jq -n --arg m "$joined" '{
  hookSpecificOutput: {
    hookEventName: "PostToolUse",
    additionalContext: $m
  }
}'
