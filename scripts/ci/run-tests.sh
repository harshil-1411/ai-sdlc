#!/bin/bash
# Runs every suite in this repository and writes JUnit XML to validation/results/,
# where `evidence gaps` (via .evidence/adapter.yml) ingests it as proof. A suite that
# fails still writes its report, and this script exits non-zero.
set -u
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
out="$root/validation/results"
mkdir -p "$out"
rc=0
run() {  # run <name> <command...>
  local name="$1"; shift
  echo "== $name"
  env -u EVIDENCE_SIGNING_KEY JUNIT_OUT="$out/$name.xml" "$@" > "$out/$name.log" 2>&1 || { rc=1; echo "   FAILED (see $out/$name.log)"; }
  tail -1 "$out/$name.log"
}
run engine     python3 "$root/plugins/evidence-sdlc/scripts/tests/engine-tests.py"
run lifecycle  python3 "$root/plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py"
run sensor     bash    "$root/plugins/evidence-sdlc/scripts/tests/template-sensor-tests.sh"
run cli        bash    "$root/cli/tests/test_cli_fixtures.sh"
run content    python3 "$root/tests/content_acceptance_tests.py"
exit $rc
