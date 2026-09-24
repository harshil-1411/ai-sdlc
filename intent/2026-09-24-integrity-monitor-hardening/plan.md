# Plan: Integrity-monitor, engine git and merge-gate hardening (security set)
Tracker: PILOT-58   From: intent/2026-09-24-integrity-monitor-hardening/spec.md   Date: 2026-09-24
Risk tier: 3 — integrity monitor, audit log, git execution in unsandboxed key-holding hooks, and the CI merge gate; policy floors `**/audit/**`, `.github/workflows/**`. A second human approves (Harshil).

Approval is not written in this file. A human records it with `/evidence-sdlc:approve <KEY> <plan-sha>`
(or `evidence approve <KEY>` in their own terminal, or an approving review in GitHub
mode); it binds to this file's hash, so any edit after approval voids it.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

Revision 3: after the second security design review. CI's trusted gate is authoritative (ADR-0004); local hardening comes with a stated residual risk (ADR-0003 rev. 2). This is the maintainer's decision.

## Files claimed
- `intent/2026-09-24-integrity-monitor-hardening/**`
- `.evidence/decisions/**`
- `plugins/evidence-sdlc/scripts/engine/integrity.py`
- `plugins/evidence-sdlc/scripts/engine/state.py`
- `plugins/evidence-sdlc/scripts/engine/hook.py`
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`
- `plugins/evidence-sdlc/scripts/engine/lifecycle.py`
- `plugins/evidence-sdlc/bin/evidence`
- `plugins/evidence-sdlc/policy/default-policy.json`
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`
- `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py`
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
- `validation/results/**` (only the human's refreshed results)

The human writes `.github/workflows/verify-range.yml` (change-controlled; see Order of work step 9). The agent does not claim it. `ci.yml` is not changed.

Revision 3.1 (third design review): the gate moves to a base-branch `pull_request_target` workflow. Approval comes from GitHub code-owner review. `verify-range` rules are tightened (fail closed, key source, per-parent audit prefix, record rollback).

## Files that change
- `plugins/evidence-sdlc/scripts/engine/state.py`:
  - `run_git`, `run_gh`, `_child_env()` (removes `GIT_*` and `EVIDENCE_SIGNING_KEY`), `check_git_config` (`-z --show-scope --show-origin --includes`) (REQ-IMH-09, 24);
  - `remove_file` (REQ-IMH-01) and the `_read_violations` `lstat` check (REQ-IMH-02);
  - `audit_verify` seen-hash and session checks (REQ-IMH-11);
  - `ENGINE_VERSION` becomes 2.1.0;
  - `git()` at `:41` becomes a thin wrapper over `run_git`.
- `plugins/evidence-sdlc/scripts/engine/integrity.py`:
  - the no-follow walk, safe restore and remove, and violations for symlinks, non-files and refused removals, audit paths included (REQ-IMH-01);
  - directory identity in `_extras` (REQ-IMH-05);
  - untracked deletes (REQ-IMH-07);
  - the snapshot safe write, plus reads with O_NOFOLLOW, fstat and a size cap (REQ-IMH-08);
  - the audit prefix hash, and new logs must verify (REQ-IMH-20);
  - `is_git` / git-dir in the snapshot, with fail-closed handling (REQ-IMH-23);
  - the 5 direct git calls go through `run_git`.
- `plugins/evidence-sdlc/scripts/engine/hook.py`:
  - `run_post`: `audit-unwritable` (REQ-IMH-06) and `git-config-refused` handling (REQ-IMH-09);
  - `run_pre`: deny when `.git` is present but git fails (REQ-IMH-23).
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`: commit flag and one-command denials, and the spoof list (REQ-IMH-10); direct git calls go through `run_git`.
- `plugins/evidence-sdlc/scripts/engine/lifecycle.py`:
  - `_gh` goes through `run_gh` with `--repo` (REQ-IMH-24);
  - new `cmd_verify_range`, registered as `verify-range` (REQ-IMH-19).
- `plugins/evidence-sdlc/bin/evidence`: add `verify-range` to the `LIFECYCLE` dispatch set.
- `plugins/evidence-sdlc/policy/default-policy.json`:
  - `git_allowed_config` (the four exact git-lfs pairs);
  - reconcile `deny_git_config_keys` with the spec's union;
  - `verify_range_blob_cap_mb: 20` and `verify_range_allow_large: []`.
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`: `suite_pilot58` with a case per engine Proof row, including marker scripts and the AST scan.
- `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py`: `verify-range` fixture repositories (REQ-IMH-19).
- `tests/content_acceptance_tests.py`: REQ-IMH-18 and REQ-IMH-21 (the workflow step is present).
- Docs, governance and release (REQ-IMH-18):
  - `docs/gates-reference.md` and `docs/managed-settings.md`: the local push gate is advisory, `sign-and-gate` is authoritative, and the allow-list path;
  - `docs/policy-reference.md`: the new keys;
  - `governance/control-mapping.md` and `governance/supplier-audit-packet.md`: change control rests on the CI gate, and the ADR-0003 §4 residual risk is stated;
  - `HANDOFF.md`;
  - `CHANGELOG.md` `## 2.1.0`, with a redeploy note and the Known issues left to PILOT-59/60/61;
  - versions go to 2.1.0.

## Order of work
1. Write the failing tests for every Proof row. Run them and record why each fails.
2. `run_git`, `run_gh`, `_child_env` and `check_git_config`; route every engine subprocess through them; the AST scan test (REQ-IMH-09, 22, 24). **Do this first, in small steps, running the engine suite after each.** Hooks read this code live, and an error blocks this session's own calls.
3. REQ-IMH-23 (fail-closed git), REQ-IMH-01, 02, 08.
4. REQ-IMH-05, 06, 07, 20.
5. **CHECKPOINT:** re-read spec.md and ADR-0003/0004. Run the full engine suite: every existing case passes, or is listed here with the reason. Then run the **security-reviewer on steps 2–4 alone**.
6. REQ-IMH-10 and REQ-IMH-11. Run `evidence audit verify` on this repository's real logs: they must pass, with only the three known fork notes.
7. REQ-IMH-19: `verify-range` with fixture-repository tests. Run it on this branch against `origin/main`, and it must pass.
8. REQ-IMH-18: docs, governance, CHANGELOG, versions.
9. **Human step (change-controlled file):** write `.github/workflows/verify-range.yml` from the spec (REQ-IMH-21 Design). The agent drafts the exact YAML in the PR description for the human to copy. The human commits it on this branch. REQ-IMH-21's content test then passes.
10. Run the engine, lifecycle and content suites directly (no JUNIT_OUT). Confirm nothing under `validation/` changed.
11. Reviewers one at a time, with no edits during a run: code-reviewer, security-reviewer, then the verifier last. Fix what this change introduced; list anything pre-existing for PILOT-59/60/61.
12. Commit and push. The maintainer opens the PR from their own GitHub account. The human runs `run-tests.sh` twice and commits results (until PILOT-60).

    **Bootstrap:** `pull_request_target` runs `main`'s workflows, so this PR itself is not gated by `verify-range`. No guard is needed, and it's enforced from the next PR. The human merges (admin) and releases.

    **Owner actions after the merge:**
    - add `verify-range` as a required status check on `main`;
    - confirm "Require review from Code Owners" is on.

Steps 3 and 4 are independent after step 2. Step 7 is independent of steps 3–6.

## Mid-flight checkpoint (Tier 2/3)
Step 5.

## Reuse decisions
- Safe IO reuses `write_file` / `_dir_fd`; only `remove_file` is new.
- The config deny set extends the policy `deny_git_config_keys`: one list for the `git -c` gate and the hook's own git.
- `verify-range` reuses `plan_claims` / `claim_matches`, `secretscan`, `audit_verify` and `signing.verify`. It lives in the lifecycle CLI, which the trusted job already runs.
- `sign-and-gate` is unchanged. The authoritative check lives in a separate base-branch `pull_request_target` workflow, because a `pull_request` workflow runs the PR's own workflow file (third review N1).

## Risks
- **Step 2 can block this session.** Mitigation: `run_git` has the same return contract as `git()`, and the engine suite runs after each sub-step. Rollback: revert `state.py`.
- **Step 7 false failures** (for example human merge commits from `main` into the branch). Commits reachable from the base are excluded by `base..head`. Merge commits are checked by `--cc`, which reports only paths that differ from every parent, so a clean merge of `main` reports nothing.
- **Bootstrap:** this PR is not gated by `verify-range` (it's not yet on `main`). This is stated in the PR and CHANGELOG, and MAN-IMH-01 checks the next PR live.
- **A `pull_request_target` misuse** (checking out PR code) would hand secrets to PR code. The REQ-IMH-21 content test forbids a head checkout, and the security-reviewer checks the YAML.
- **Refused local git config** in adopters' repositories: the message names the allow path, and the owner accepts this at approval.
- **Size:** estimate 1,000–1,400 changed lines [NEEDS VERIFICATION after step 1].

## Proof

| REQ ID | Requirement | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-IMH-01 | No removal or restore through symlinks or outside the repository; symlink, non-file and refused-removal violations | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-01 …" | CI engine.xml |
| REQ-IMH-02 | A non-regular violations path is an open violation | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-02 …" | CI engine.xml |
| REQ-IMH-05 | `.evidence` directory type, mode, owner and identity changes are violations | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-05 …" | CI engine.xml |
| REQ-IMH-06 | An unwritable post-call audit entry records a violation, and the next call is denied | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-06 …" | CI engine.xml |
| REQ-IMH-07 | Deleting an untracked file is judged | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-07 …" | CI engine.xml |
| REQ-IMH-08 | Snapshots written and read safely; a link, non-file or oversize snapshot is a violation | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-08 …" | CI engine.xml |
| REQ-IMH-09 | Engine git neutralised; `GIT_*` and the key removed from children; config refusal per ADR-0003 §2; marker scripts never run | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-09 …" | CI engine.xml |
| REQ-IMH-10 | Commit flag and one-command denials; index and object environment variables are spoofing | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-10 …" | CI engine.xml |
| REQ-IMH-11 | Replayed and cross-session audit entries break verification | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-11 …" | CI engine.xml |
| REQ-IMH-19 | `verify-range` per ADR-0004 rev. 2. Each fixture fails: evil merge, trailer-less or CODEOWNER-authored trailer-less commit, unclaimed A/M/D/T/R, truncated, omitted or deleted audit log, violations rollback, state regression, replayed key, no key, empty SHA, no approving review, secret. A clean branch after `main` moved passes | CLI | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-IMH-19 …" (GitHub API stubbed) | CI lifecycle.xml |
| REQ-IMH-20 | The audit-log prefix hash detects truncation, rewrite and replacement; new logs must verify | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-20 …" | CI engine.xml |
| REQ-IMH-21 | `verify-range.yml` runs on `pull_request_target` from the base; no head checkout, no `continue-on-error` or `\|\| true`; permissions and event conditions set | content | yes | — | `tests/content_acceptance_tests.py` "REQ-IMH-21 …" | CI content.xml |
| REQ-IMH-22 | No engine subprocess bypasses the approved helpers | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-22 …" | CI engine.xml |
| REQ-IMH-23 | Git failure fails closed: violation, filesystem restore, next pre denied | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-23 …" | CI engine.xml |
| REQ-IMH-24 | `gh` pinned to `--repo`, with `GIT_*` and the key removed | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-24 …" | CI engine.xml |
| REQ-IMH-18 | Docs, governance, HANDOFF and Known issues match: local advisory, CI authoritative, residual risk stated | content | yes | — | `tests/content_acceptance_tests.py` "REQ-IMH-18 …" | CI content.xml |
| MAN-IMH-01 | Live: on the PR after this merges, `sign-and-gate` runs `verify-range` and fails a deliberately bad test branch | manual | no | MAN-IMH-01 | — | CI run link in the release note |

## Considered and rejected
- **ADR-0001, and the local push-time range check.** Both were rejected in the design reviews (see the spec's scope history).
- **The agent editing `ci.yml`** without a `CHANGE_TICKET` session. It's change-controlled, so step 9 is a human edit.
- **A `verify-range` step in `ci.yml` `sign-and-gate`.** On `pull_request`, the PR's own workflow file runs, so a PR could remove the gate (third review N1).
