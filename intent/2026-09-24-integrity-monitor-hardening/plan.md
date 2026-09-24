# Plan: Integrity-monitor and engine git hardening (security set)
Tracker: PILOT-58   From: intent/2026-09-24-integrity-monitor-hardening/spec.md   Date: 2026-09-24
Risk tier: 3 — integrity monitor, audit log, commit and push gates, and git execution in unsandboxed, key-holding hooks; policy floor `**/audit/**`. A second human approves (Harshil).

Approval is not written in this file. A human records it with `/evidence-sdlc:approve <KEY> <plan-sha>`
(or `evidence approve <KEY>` in their own terminal, or an approving review in GitHub
mode); it binds to this file's hash, so any edit after approval voids it.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

Revision 2: rewritten after the security design review. ADR-0001 was rejected; the change was split into PILOT-58/59/60 by the maintainer's decision.

## Files claimed
- `intent/2026-09-24-integrity-monitor-hardening/**`
- `.evidence/decisions/**`
- `plugins/evidence-sdlc/scripts/engine/integrity.py`
- `plugins/evidence-sdlc/scripts/engine/state.py`
- `plugins/evidence-sdlc/scripts/engine/hook.py`
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`
- `plugins/evidence-sdlc/scripts/engine/lifecycle.py`
- `plugins/evidence-sdlc/policy/default-policy.json`
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`
- `tests/content_acceptance_tests.py`
- `docs/managed-settings.md`
- `docs/policy-reference.md`
- `docs/gates-reference.md`
- `governance/control-mapping.md`
- `governance/supplier-audit-packet.md`
- `HANDOFF.md`
- `CHANGELOG.md`
- `plugins/*/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `validation/results/**` (only if the human commits refreshed results; the agent does not write here)

## Files that change
- `plugins/evidence-sdlc/scripts/engine/state.py`:
  - `run_git` (REQ-IMH-09): replaces the body of `git()` at `:41`, which becomes a thin wrapper;
  - `check_git_config` and `GIT_EXEC_DENY` (REQ-IMH-09);
  - `remove_file` (REQ-IMH-01);
  - `_read_violations` `lstat` check (REQ-IMH-02);
  - `audit_verify` seen-hash and session checks (REQ-IMH-11);
  - `ENGINE_VERSION` becomes 2.1.0.
- `plugins/evidence-sdlc/scripts/engine/integrity.py`:
  - `_control_plane_files` no-follow walk; restore and remove through the safe helpers (REQ-IMH-01);
  - `.evidence` directory `lstat` in `_extras` (REQ-IMH-05);
  - untracked deletes (REQ-IMH-07);
  - `_snap_path` hardening (REQ-IMH-08);
  - audit prefix hash (REQ-IMH-20);
  - its 5 direct git calls go through `st.run_git` (REQ-IMH-22).
- `plugins/evidence-sdlc/scripts/engine/hook.py`: `run_post` records `audit-unwritable` (REQ-IMH-06); post-time `git-config-refused` handling (REQ-IMH-09).
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`:
  - `_check_commit` flag and one-command denials (REQ-IMH-10);
  - spoof-list additions (REQ-IMH-10);
  - push gate: `range_problems` (REQ-IMH-19) and the missing-state denial (REQ-IMH-21);
  - direct git calls go through `st.run_git`.
- `plugins/evidence-sdlc/scripts/engine/lifecycle.py`: direct git calls (if any) go through `st.run_git` (REQ-IMH-22).
- `plugins/evidence-sdlc/policy/default-policy.json`: `git_allowed_config` with the four exact git-lfs key=value pairs.
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`: a new `suite_pilot58` covering every Proof row, with marker-script tests for REQ-IMH-09.
- `tests/content_acceptance_tests.py`: REQ-IMH-18.
- Docs and governance (REQ-IMH-18):
  - `docs/policy-reference.md`: `git_allowed_config` and the extended deny set;
  - `docs/gates-reference.md`: commit denials, the push-range check, the git-config refusal;
  - `docs/managed-settings.md`: an allow-list note for LFS and other filters;
  - `governance/control-mapping.md` and `governance/supplier-audit-packet.md`: change-control and audit claims;
  - `HANDOFF.md`: state, and the PILOT-59/60 scope;
  - `CHANGELOG.md` `## 2.1.0`: a redeploy note and the remaining Known issues;
  - five plugin.json files and marketplace.json go to 2.1.0.

## Order of work
1. Write the failing tests for every Proof row in `suite_pilot58`. Run them and record why each fails.
2. `state.run_git` + `check_git_config`; route every engine git call through it; the REQ-IMH-22 scan test. **Do this first:** later steps run git inside the hook, and a mistake here blocks this session's own calls, so run the suite after each sub-step.
3. REQ-IMH-01, 02, 08: safe removal and restore, the no-follow walk, the violations `lstat` check, the snapshot directory.
4. REQ-IMH-05, 06, 07, 20: directory checks, own-log failure, untracked deletes, audit prefix hash.
5. **CHECKPOINT:** re-read spec.md and ADR-0003. Run the full engine suite: every existing case passes, or is listed here with the reason. Then run the **security-reviewer on steps 2–4 alone**, before the commit and push work.
6. REQ-IMH-10, 19, 21: commit-time denials, the push-time range check, the missing-state push denial. This is the riskiest step for false denials on legitimate pushes.
7. REQ-IMH-11: audit_verify seen-hash and session binding. Run `evidence audit verify` on this repository's real logs: they must still pass, with only the three known fork notes.
8. REQ-IMH-18: docs, governance, CHANGELOG, versions.
9. Run the engine, lifecycle and content suites directly (no JUNIT_OUT). Confirm nothing under `validation/` changed.
10. Reviewers one at a time, with no edits during a run: code-reviewer, security-reviewer, then the verifier last. Fix what this change introduced; list anything pre-existing for PILOT-59/60.
11. Commit, then push. The push gate now runs REQ-IMH-19 on this branch itself. Open the PR with `gh` from the maintainer's own account (the second-person route). The human runs `run-tests.sh` twice and commits results (still needed until PILOT-60). The human merges and releases.

Steps 3 and 4 are independent after step 2. Step 7 is independent of step 6.

## Mid-flight checkpoint (Tier 2/3)
Step 5.

## Reuse decisions
- Safe IO reuses `write_file` / `_dir_fd` (2.0.1); only `remove_file` is new.
- The deny set extends the existing policy key `deny_git_config_keys` (docs/policy-reference.md:93), so the `git -c` gate and the hook's own git share one list.
- The push-range check reuses the existing claims matcher (`st.claim_matches`), `secretscan`, and the evidence-file list from `_check_commit`.
- Snapshot-restore is kept (no ADR-0001).

## Risks
- **Step 2 can block this session.** Hooks read engine code live, so a wrong `run_git` makes every PreToolUse fail closed. Mitigation: implement `run_git` as a drop-in with the same return contract as `git()`, and run the engine suite before the next edit. Rollback: revert `state.py`.
- **Step 6 can deny legitimate pushes.** Examples: a base ref that isn't fetched, merge commits from `main`, or large binary blobs. Mitigations: with no base, fall back to the pre-commit rules and say so; merge commits from the base are skipped (only commits not reachable from the base are checked); blob scans are capped at 2 MiB each. Rollback: a policy flag `push_range_check: false` (org only).
- **Refusing local credential helpers** may surprise some repositories. The message names the allow path. The owner accepts this at approval (spec Areas of concern).
- **Size:** estimate 700–1000 changed lines [NEEDS VERIFICATION after step 1].

## Proof

| REQ ID | Requirement | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-IMH-01 | No removal or restore through a symlinked component or outside the repository; a symlink at a control-plane path is a violation | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-01 …" | CI engine.xml |
| REQ-IMH-02 | A non-regular violations path is an open violation | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-02 …" | CI engine.xml |
| REQ-IMH-05 | A change to a `.evidence` directory's type, mode or owner is a violation | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-05 …" | CI engine.xml |
| REQ-IMH-06 | An unwritable post-call audit entry records a violation, and the next call is denied | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-06 …" | CI engine.xml |
| REQ-IMH-07 | Deleting an untracked file is judged | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-07 …" | CI engine.xml |
| REQ-IMH-08 | The snapshot directory is safe; a planted link fails closed | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-08 …" | CI engine.xml |
| REQ-IMH-09 | Engine git neutralised and `GIT_*` scrubbed; denied local/worktree config refused (exact-value allow-list); a marker script never runs | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-09 …" | CI engine.xml |
| REQ-IMH-10 | Commit flag and one-command denials; index and object environment variables are spoofing | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-10 …" | CI engine.xml |
| REQ-IMH-11 | Replayed and cross-session audit entries break verification | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-11 …" | CI engine.xml |
| REQ-IMH-19 | The push gate validates every commit's tree in the branch range: claims, evidence, secrets | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-19 …" | CI engine.xml |
| REQ-IMH-20 | The audit-log prefix hash detects truncation, rewrite or replacement | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-20 …" | CI engine.xml |
| REQ-IMH-21 | Push denied when a keyed change's state is missing or invalid | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-21 …" | CI engine.xml |
| REQ-IMH-22 | No engine git call bypasses `run_git` | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-22 …" | CI engine.xml |
| REQ-IMH-18 | Docs, governance, HANDOFF and Known issues match the shipped behaviour | content | yes | — | `tests/content_acceptance_tests.py` "REQ-IMH-18 …" | CI content.xml |

## Considered and rejected
- **ADR-0001 (signature validation instead of restore, a monitor lease).** Rejected in design review (replay, lease bypass). Concurrency moves to PILOT-59.
- **Hand-parsing `.git/config`.** See ADR-0003's alternatives.
- **Doing the usability items here.** Moved to PILOT-60 to keep this Tier 3 change reviewable.
