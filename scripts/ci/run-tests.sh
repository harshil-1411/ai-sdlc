#!/bin/bash
# Runs every suite in this repository and writes JUnit XML and logs to EVIDENCE_RESULTS_DIR
# (ADR-0002 rev. 2). The default is outside the working tree, so a local run changes nothing
# under version control: ${TMPDIR:-/tmp}/evidence-chain-results/<repo>-<12 hex of the root's sha256>.
# CI sets EVIDENCE_RESULTS_DIR to ${{ runner.temp }}/results, uploads it, and signs only that
# artifact. The last step is this repository's own `evidence gaps --strict --self-check` over
# the fresh results, written to self-check.xml as the proof of REQ-V2C-09. A suite that fails
# still writes its report, and this script exits non-zero.
set -u
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
name="$(basename "$root")-$(printf '%s' "$root" | python3 -c 'import hashlib, sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest()[:12])')"
out="${EVIDENCE_RESULTS_DIR:-${TMPDIR:-/tmp}/evidence-chain-results/$name}"
# a results directory inside the working tree would put results under version control, and the
# rm -f below would delete files there: refuse it (real paths, so a link or ../ cannot hide it)
real_out="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$out")" || exit 2
real_root="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$root")" || exit 2
# macOS file systems are case-insensitive by default: compare lowercased paths there
if [ "$(uname)" = Darwin ]; then real_out="$(printf '%s' "$real_out" | tr '[:upper:]' '[:lower:]')"; real_root="$(printf '%s' "$real_root" | tr '[:upper:]' '[:lower:]')"; fi
case "$real_out/" in "$real_root"/*) echo "EVIDENCE_RESULTS_DIR ($out) is inside the working tree ($root); use a directory outside it" >&2; exit 2;; esac
mkdir -p "$out"
# a stale suite from an earlier run must never count
rm -f "$out"/*.xml "$out"/*.log "$out"/*.sig
echo "results directory: $out"
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
# Final step (REQ-USA-02): this repository passes its own strict gate over this run's results only.
echo "== self-check"
sc=pass
(cd "$root" && env -u EVIDENCE_SIGNING_KEY python3 "$root/plugins/evidence-sdlc/bin/evidence" gaps --strict --self-check --only-results --results "$out") > "$out/self-check.log" 2>&1 || { sc=fail; rc=1; }
printf '%s\t%s\n' "$sc" "REQ-V2C-09 this repository passes its own evidence gaps --strict (run-tests.sh final step)" \
  | python3 "$root/plugins/evidence-sdlc/scripts/tests/junit_from_tsv.py" "self-check" "$out/self-check.xml"
echo "results directory: $out"
if [ "$sc" = pass ]; then
  echo "self-check: passed"
else
  echo "self-check: FAILED (see $out/self-check.log)"
  awk '/^[A-Z].*\[blocking\]$/ { b = !/\(0\)/; if (b) print; next } /^[A-Z]/ { b = 0 } b && /^  - /' "$out/self-check.log" | head -20
fi
echo "to check locally, pass these results: evidence gaps --strict --results \"$out\""
exit $rc
