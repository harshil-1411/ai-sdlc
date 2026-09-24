#!/bin/bash
# Fails when a plugin's files changed relative to the base ref but its plugin.json
# "version" did not. Why: with a static version, `/plugin update` treats an
# unchanged version as "no update" and silently keeps users on stale code -- the
# reason versions were reverted twice before (PILOT-13, PILOT-15). Versions are
# kept, and this check makes forgetting a bump impossible to merge.
# Usage: scripts/ci/check-version-bump.sh [base-ref]   (default: origin/main, then main)
set -u
base="${1:-}"
if [ -z "$base" ]; then
  for c in origin/main main origin/master master; do
    git rev-parse --verify -q "$c" >/dev/null && { base="$c"; break; }
  done
fi
[ -z "$base" ] && { echo "check-version-bump: no base ref found; nothing to compare"; exit 0; }
fail=0
for dir in plugins/*/; do
  name=$(basename "$dir")
  manifest="$dir.claude-plugin/plugin.json"
  [ -f "$manifest" ] || continue
  changed=$(git diff --name-only "$base"...HEAD -- "$dir" | grep -v -E '/evals/results/' | grep -v -E '/evals/.*SUMMARY\.md$' || true)
  [ -z "$changed" ] && continue
  new=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("version",""))' "$manifest")
  old=$(git show "$base:$manifest" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("version",""))' 2>/dev/null || echo "")
  if [ -z "$new" ]; then
    echo "FAIL $name: plugin.json has no version"; fail=1
  elif [ "$new" = "$old" ]; then
    echo "FAIL $name: files changed since $base but version is still $new -- bump it and add a CHANGELOG entry"; fail=1
  else
    echo "ok   $name: ${old:-none} -> $new"
  fi
done
exit $fail
