# Plan: v2 enterprise hardening
Tracker: PILOT-53   From: spec.md   Approved by: suparn.bector@msbdocs.com (maintainer) — standing instruction 2026-09-24: "Lets start fixing the issues identified … do not stop until everything reported in v1 audit report has been fixed". Approval was given before this plan was written, so this plan is presented at the end of the run for after-the-fact review.   Date: 2026-09-24

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

Concurrency: the only other plans on disk (TRACE-1 gate-regression-tests, PILOT-50,
PILOT-51) are completed and committed. Branch `hardening/v2` is the only working branch.

## Files claimed
- `plugins/evidence-sdlc/scripts/**`, `plugins/evidence-sdlc/hooks/hooks.json`,
  `plugins/evidence-sdlc/policy/**`, `plugins/evidence-sdlc/bin/**`,
  `plugins/evidence-sdlc/commands/**`, `plugins/evidence-sdlc/agents/**`,
  `plugins/evidence-sdlc/skills/**`, `plugins/evidence-sdlc/templates/**`
- `plugins/evidence-quality/scripts/**`, `plugins/evidence-quality/hooks/hooks.json`,
  `plugins/evidence-quality/skills/**`, `plugins/evidence-quality/agents/**`
- `plugins/evidence-discovery/scripts/**`, `plugins/evidence-discovery/skills/**`
- `plugins/evidence-compliance/skills/**`, `plugins/evidence-compliance/agents/**`
- `plugins/evidence-integrations/skills/**`
- `plugins/*/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
- `plugins/*/evals/**`
- `cli/**`
- `governance/**`, `docs/**`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`,
  `CHANGELOG.md` (new), `managed-settings.json`, `pipeline.example.yml`,
  `examples/**`, `.github/workflows/**` (new), `.gitignore`, `.evidenceignore` (new),
  `validation/traceability.csv`
- `intent/2026-09-24-testing-depth-and-strategy-interview/spec.md` (REQ rename only)

## Files that change
All the "Files claimed" paths exist, except the ones marked new. Their parent
directories exist, apart from `.github/` and `plugins/evidence-sdlc/{policy,bin,commands}/`,
which are created here.

## Order of work
Work streams 2, 3 and 4a run in parallel with work stream 1. Streams 4b, 5 and 6
depend on stream 1.

1. **WS1 — Gate engine** (me). `scripts/engine/` holds `evidence_policy.py` (decide),
   `cmdparse.py` (shlex-based command analysis), `secrets.py`, `state.py` (the
   change/approval/audit model shared with the CLI), `hook.py` (I/O), and
   `default-policy.json`. There is a table-driven regression suite that covers every
   v1 probe. The old `.sh` gates stay on disk, unchanged, until step 7.
   (REQ-V2G-01..12, REQ-V2S-02, -03, REQ-V2A-02, -03, REQ-V2K-01, REQ-V2X-01)
2. **WS2 — CLI traceability** (agent, `cli/evidence` traceability functions only).
   (REQ-V2C-02..06, -08, -10, REQ-V2X-02, REQ-V2O-04)
3. **WS3 — Content** (agent). Skills, agents, templates, ADR, release-readiness,
   and the OWASP API coverage in secure-api-review.
   (REQ-V2R-*, REQ-V2D-01..07, -10, REQ-V2K-03, -04)
4. **WS4a — Control sets** (agent). ISO 27001 and NIST SSDF control sets,
   plus owner-placeholder handling. (REQ-V2O-02 control sets, REQ-V2O-03)
5. **CHECKPOINT.** Re-check WS1–WS4a against spec.md. Run the engine suite, the
   old gate suites and the CLI suite. Record any drift here.
6. **WS1b — CLI lifecycle** (me): `bin/evidence` with the change/approve/audit/metrics
   commands; `cli/evidence` becomes a shim; commands/*.md.
   (REQ-V2S-01, -04, REQ-V2A-01, REQ-V2C-01, -07, -09, REQ-V2D-08, -09, REQ-V2P-03)
7. **Switch-over** (me): rewrite `hooks.json` for both plugins to call the engine,
   including the SubagentStop and PostToolUse audit hooks. Turn the old `.sh` gates
   into shims. Update the sensor and require-repo-profile. Update managed-settings.
   (REQ-V2K-02, REQ-V2A-04, REQ-V2P-04 commit-gate move)
8. **WS4b — Governance** (agent, after 7): correct the overclaims and write
   control-mapping.md, citing the engine tests. (REQ-V2O-01, -02 mapping)
9. **WS5 — Product** (me and an agent): versions, the bump check, CHANGELOG,
   metadata, CI, reference pipelines, the README split, hygiene, and install docs.
   (REQ-V2P-*)
10. **WS6 — Evals**: new cases, rewrites of non-discriminating cases, the full 3-run
    baselined pass, and committed summaries. (REQ-V2E-*)
11. **Self-check**: `evidence gaps` on this repo (REQ-V2C-09), all suites, and
    `claude plugin validate`.
12. **Re-audit**: independent agents given the v1 rubric; live scenarios re-run
    outside `/tmp` in a new session that loads the new hooks; then the v1-vs-v2 report.

## Mid-flight checkpoint (Tier 2/3)
Step 5 is marked `CHECKPOINT`.

## Reuse decisions
- The CLI's graph builder is extended, not rewritten.
- The existing gate regression suite is kept and re-pointed at the shims, so all
  34 historical cases continue to guard against regressions.
- The template sensor keeps its advisory contract.

## Risks
- **Riskiest: step 7.** The switch-over changes the hooks every new session loads.
  Rollback: revert the hooks.json commits; the old scripts stay in history.
  This session is unaffected because hooks are loaded at session start
  [NEEDS VERIFICATION: behaviour on hooks.json change mid-session].
- **Bash write detection false positives.** Mitigated by the table-driven allow
  cases (reads, grep, tests, git status and log).
- **Eval spend.** Capped by `--max-cost-usd` per plugin, total ≤ $80.

## Proof
| REQ ID | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- |
| REQ-V2G-01..12, V2S-02, V2S-03, V2A-03, V2K-01, V2X-01 | unit (engine) | Yes | engine case IDs | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` | test stdout |
| REQ-V2S-01, V2S-04, V2A-01, V2A-02, V2C-01..10, V2X-02, V2O-04, V2D-09 | CLI fixtures | Yes | fixture IDs | `cli/tests/test_cli_fixtures.sh` + `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.sh` | test stdout |
| REQ-V2D-*, V2R-*, V2K-03, V2K-04, V2E-* | eval | Yes | case dirs | `claude plugin eval` | `evals/SUMMARY.md` |
| REQ-V2O-*, V2P-*, V2A-04 | review + scripts | Partly | — | `ci/check-*.sh` | CI script output |

## Considered and rejected
See spec.md "Rejected alternatives".
