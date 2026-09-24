#!/bin/bash
# Fails when a plugin's files changed relative to the base ref but its plugin.json
# "version" was not raised, or when CHANGELOG.md has no entry for the new version.
# Why: with a static version, `/plugin update` treats an unchanged version as "no
# update" and silently keeps users on stale code -- the reason versions were reverted
# twice before (PILOT-13, PILOT-15). Versions are kept; this makes a missed bump,
# a downgrade, or an undocumented release impossible to merge.
# Usage: scripts/ci/check-version-bump.sh [base-ref]   (default: origin/main, then main)
set -u
base="${1:-}"
if [ -z "$base" ]; then
  for c in origin/main main origin/master master; do
    git rev-parse --verify -q "$c" >/dev/null && { base="$c"; break; }
  done
  [ -z "$base" ] && { echo "check-version-bump: no base ref found (tried origin/main, main, origin/master, master)"; exit 1; }
fi
if ! git rev-parse --verify -q "$base" >/dev/null; then
  echo "FAIL: base ref '$base' does not exist -- refusing to pass without a comparison (fetch it first)"
  exit 1
fi
fail=0
ver_of() { python3 -c 'import json,sys; print(json.load(sys.stdin).get("version",""))' 2>/dev/null; }
newer() {  # newer <new> <old>: true when new > old (semver, numeric parts)
  python3 - "$1" "$2" <<'PY'
import re, sys
def parse(v):
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v or "")
    return tuple(int(x) for x in m.groups()) if m else None
new, old = parse(sys.argv[1]), parse(sys.argv[2])
sys.exit(0 if new and (old is None or new > old) else 1)
PY
}
for dir in plugins/*/; do
  name=$(basename "$dir")
  manifest="$dir.claude-plugin/plugin.json"
  [ -f "$manifest" ] || continue
  changed=$(git diff --name-only "$base"...HEAD -- "$dir" | grep -v -E '/evals/results/' || true)
  [ -z "$changed" ] && continue
  new=$(ver_of < "$manifest")
  old=$(git show "$base:$manifest" 2>/dev/null | ver_of || echo "")
  if [ -z "$new" ]; then
    echo "FAIL $name: plugin.json has no version"; fail=1; continue
  fi
  if ! newer "$new" "$old"; then
    echo "FAIL $name: files changed since $base but version $new is not higher than ${old:-none}"; fail=1; continue
  fi
  if ! grep -Eq "^## +\[?$new\]?( |$)" CHANGELOG.md 2>/dev/null; then
    echo "FAIL $name: version $new has no '## $new' entry in CHANGELOG.md"; fail=1; continue
  fi
  echo "ok   $name: ${old:-none} -> $new"
done
exit $fail
