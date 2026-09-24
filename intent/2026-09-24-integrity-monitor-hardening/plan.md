# Plan: Integrity-monitor and engine hardening
Tracker: PILOT-58   From: intent/2026-09-24-integrity-monitor-hardening/spec.md   Date: 2026-09-24
Risk tier: 3 — integrity monitor, audit log, commit gate and git execution in unsandboxed, key-holding hooks; policy floor `**/audit/**`; changes the framework's tamper-evidence claims. A second human approves (Harshil).

Approval is not written in this file. A human records it with `/evidence-sdlc:approve <KEY> <plan-sha>`
(or `evidence approve <KEY>` in their own terminal, or an approving review in GitHub
mode); it binds to this file's hash, so any edit after approval voids it.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Files claimed
- `intent/2026-09-24-integrity-monitor-hardening/**`
- `.evidence/decisions/**`
- `.evidence/adapter.yml`
- `plugins/evidence-sdlc/scripts/engine/integrity.py`
- `plugins/evidence-sdlc/scripts/engine/state.py`
- `plugins/evidence-sdlc/scripts/engine/hook.py`
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`
- `plugins/evidence-sdlc/scripts/engine/lifecycle.py`
- `plugins/evidence-sdlc/scripts/cli/evidence_trace.py`
- `plugins/evidence-sdlc/policy/default-policy.json`
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`
- `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py`
- `tests/content_acceptance_tests.py`
- `scripts/ci/run-tests.sh`
- `docs/managed-settings.md`
- `docs/policy-reference.md`
- `docs/gates-reference.md`
- `governance/control-mapping.md`
- `governance/supplier-audit-packet.md`
- `HANDOFF.md`
- `CHANGELOG.md`
- `plugins/*/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`

Not claimed:
- `.github/workflows/ci.yml` is change-controlled. `run-tests.sh` detects CI through `GITHUB_ACTIONS`, so the workflow needs no edit.
- `validation/results/**` becomes historical (ADR-0002) and is not touched.

## Files that change
- `plugins/evidence-sdlc/scripts/engine/state.py`
  - `run_git(args, cwd)`, used by `git()` at `:41`:
    - prepends `-c core.fsmonitor=false -c core.hooksPath=/dev/null -c core.pager=cat -c diff.external= -c protocol.ext.allow=never`;
    - sets `GIT_CONFIG_NOSYSTEM=1`;
    - calls `check_git_config(root)` first, which parses `.git/config` and its `include.path` files and refuses keys matching policy `deny_git_config_keys` unless they match `git_allowed_config` (REQ-IMH-09).
  - `remove_file(root, rel)`: unlinks through `_dir_fd`; never outside root (REQ-IMH-01).
  - `_read_violations`: `lstat` first, and a non-regular file is an open violation (REQ-IMH-02).
  - `audit_verify`: a set of seen hashes, so a repeat is a break (REQ-IMH-11).
  - `SIGNED_RECORDS` globs and `quarantine(root, rel)` (REQ-IMH-03).
  - `ENGINE_VERSION` becomes 2.1.0.
- `plugins/evidence-sdlc/scripts/engine/integrity.py`
  - `_control_plane_files`: `os.walk(followlinks=False)` + `lstat`; symlinks reported (REQ-IMH-01).
  - `check()`:
    - signed records are verified and quarantined, never restored or removed (REQ-IMH-03);
    - unsigned config is restored through `state.write_file` and removed through `state.remove_file` (REQ-IMH-01);
    - untracked-status deletes are judged (REQ-IMH-07);
    - the `lstat` (type, mode, uid) of the four `.evidence` directories is compared in `_extras` (REQ-IMH-05).
  - `_snap_path`: `<tempdir>/evidence-chain-snapshots-<uid>/<session>`, 0700, `lstat`-checked, written through `write_file` (REQ-IMH-08).
  - Lease: `acquire_lease(ctx)` / `release_lease(ctx)` on `.git/evidence-monitor.lease` (O_EXCL, TTL, owner token), with the token stored in the snapshot (REQ-IMH-04).
  - The 5 direct `subprocess.run(["git", …])` calls go through `st.run_git`.
- `plugins/evidence-sdlc/scripts/engine/hook.py`
  - `run_pre`: acquire the lease before `integrity.snapshot`, and deny if not acquired within `monitor_lease_wait_s` (REQ-IMH-04).
  - `run_post`: release the lease after `run_integrity`. If the post `_audit` fails, record an `audit-unwritable` violation (REQ-IMH-06).
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`
  - `_check_commit` (`:393` onward):
    - deny a pathspec, `--only`/`-o` or `--include`/`-i`;
    - for `-a`, check staged ∪ `git diff --name-only`, and scan secrets in the working-tree content (REQ-IMH-10).
  - The temp-argument loop (`:779-785`) applies only to programs in `EXECUTES_ARG` (REQ-IMH-15).
  - Its direct git calls go through `st.run_git`.
- `plugins/evidence-sdlc/scripts/engine/lifecycle.py`: `write_approval` always appends a history entry (`approved` or `re-approved`) (REQ-IMH-17).
- `plugins/evidence-sdlc/scripts/cli/evidence_trace.py`:
  - YAML reader strips ` #` comments outside quotes (REQ-IMH-13);
  - the requirement scan reads specs before plan globs, and a plan ID already defined by a spec is a reference (REQ-IMH-14);
  - honours `self_check_requirement` (REQ-IMH-12).
- `plugins/evidence-sdlc/policy/default-policy.json`: new keys `monitor_lease_wait_s: 15`, `monitor_lease_ttl_s: 600`, `git_allowed_config: ["filter.lfs.*"]`.
- `.evidence/adapter.yml`: `self_check_requirement: REQ-V2C-09`.
- `scripts/ci/run-tests.sh` (REQ-IMH-12):
  - `EVIDENCE_RESULTS_DIR`, defaulting to `validation/results` when `GITHUB_ACTIONS=true` and otherwise `${TMPDIR:-/tmp}/evidence-results/<sha1 of repo path>`;
  - a final step `evidence gaps --strict --results "$dir"` that writes `gaps.xml` with a REQ-V2C-09 testcase and sets the exit code.
- `tests/content_acceptance_tests.py`:
  - the REQ-V2C-09 in-suite gaps block (`:296-305`) becomes a structural check on `run-tests.sh` (REQ-IMH-12);
  - add the REQ-IMH-18 docs/governance check.
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`: a new suite `suite_pilot58` with the cases in Proof; `suite_round4` creates its `s1.jsonl` itself (REQ-IMH-16).
- `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py`: REQ-IMH-17.
- Docs and governance (REQ-IMH-18):
  - `docs/managed-settings.md`: the lease, quarantine, the git-config refusal, and the hook-before-prompt note;
  - `docs/policy-reference.md`: the new keys;
  - `docs/gates-reference.md`: commit pathspec denial and temp-script rule;
  - `governance/control-mapping.md` and `governance/supplier-audit-packet.md`: records are signature-validated, with the known-issue caveats removed;
  - `HANDOFF.md`: current state; PILOT-58 items struck;
  - `CHANGELOG.md` `## 2.1.0`, with a redeploy note;
  - five plugin.json files and marketplace.json go to 2.1.0 (a minor bump: new policy keys and new denials).

## Order of work
1. Write the failing tests for REQ-IMH-01..11, 13–17 in `engine-tests.py` / `cli-lifecycle-tests.py`. Run them and record which fail for the stated reason.
2. `state.run_git` + `check_git_config`, and route every engine git call through it (REQ-IMH-09). **Do this first:** every later step runs git inside the hook.
3. Safe removal, control-plane walk, the violations `lstat` check, and snapshot-directory hardening (REQ-IMH-01, 02, 08).
4. Signed-record validation and quarantine (REQ-IMH-03), directory `lstat` checks (REQ-IMH-05), untracked deletes (REQ-IMH-07), own-log failure (REQ-IMH-06).
5. **CHECKPOINT:** re-read spec.md and ADR-0001. Run the full engine suite. Every pre-existing case must still pass, or be listed here with why it changed (the expected change is REQ-V2G-09's "restored" cases for signed records, which become "quarantined"). Run the security-reviewer on steps 2–4 alone before continuing.
6. The monitor lease (REQ-IMH-04). This is the riskiest step.
7. Commit gate (REQ-IMH-10), audit replay (REQ-IMH-11), temp-script rule (REQ-IMH-15).
8. CLI: YAML comments, spec-before-plan, self-check requirement (REQ-IMH-13, 14, 12 part). `run-tests.sh` and the content-suite change (REQ-IMH-12). History entry (REQ-IMH-17). Suite fix (REQ-IMH-16).
9. Docs, governance, CHANGELOG, versions (REQ-IMH-18).
10. Run the engine, lifecycle and content suites directly, then the full `bash scripts/ci/run-tests.sh`. That is now safe for an agent, because its results go outside the repository; confirm no `validation/` change and a single-pass green run.
11. Reviewers **one at a time**, with no edits during a run: code-reviewer, then security-reviewer, then the verifier last. Fix the findings this change introduced; list anything pre-existing for a later change.
12. Commit with the key and the `Agent-Session` trailer, push, and open the PR with `gh` (the new session setting). The human (admin) merges and releases.

Independent: steps 7 and 8 do not depend on 6 and can be done in either order.

## Mid-flight checkpoint (Tier 2/3)
Step 5.

## Reuse decisions
- Every filesystem action reuses `state.write_file` / `open_append` / `_dir_fd` from 2.0.1, plus the new `remove_file`. No second safe-IO layer.
- The git-config refusal reuses the existing policy list `deny_git_config_keys` (docs/policy-reference.md:93), which already names the command-executing keys for `git -c` / `git config`. Only the allow-list `git_allowed_config` is new.
- Signature checks reuse `signing.verify` and `state.audit_verify`.
- CI's existing `sign-and-gate` job (signed results + trusted-CLI `gaps --strict`) is the merge gate. No workflow change.

## Risks
- **Step 6 (lease) is the riskiest.** A bug can deny every Bash call, which fails closed but is disruptive. Mitigations: the lease is bounded (wait 15 s, TTL 600 s), and a test covers a crashed holder. Rollback: set `monitor_lease_wait_s: 0` in the org policy to skip the lease, then revert the hunk.
- **Step 2 (git refusal)** could refuse legitimate repos with custom filters (LFS is allowed by default). The message names `git_allowed_config`. Rollback: extend that list in the org policy.
- **Step 4 (quarantine)** changes REQ-V2G-09 behaviour for signed records. Those tests' expected results change, and each is listed in the PR.
- **Steps 1–4 touch code that runs live in this session.** Hooks read script content live, so a bug can block this session's own tool calls. Mitigation: small steps, and run the suite after each.
- **Size:** estimate 900–1400 changed lines [NEEDS VERIFICATION after step 1]. If it passes 1500, split REQ-IMH-12..17 into a separate Tier 1/2 change (spec "Rejected alternatives").

## Proof

| REQ ID | Requirement | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-IMH-01 | No removal or restore through a symlinked component, and none outside the repository | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-01 …" | CI engine.xml |
| REQ-IMH-02 | A non-regular violations path is an open violation | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-02 …" | CI engine.xml |
| REQ-IMH-03 | Signed records validated by signature, quarantined if invalid, never restored or removed | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-03 …" | CI engine.xml |
| REQ-IMH-04 | Per-repository monitor lease: wait, deny on timeout, expired-lease note, correct attribution | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-04 …" | CI engine.xml |
| REQ-IMH-05 | Changes to the `.evidence` directories' type, mode or owner are violations | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-05 …" | CI engine.xml |
| REQ-IMH-06 | An unwritable post-call audit entry records a violation, and the next call is denied | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-06 …" | CI engine.xml |
| REQ-IMH-07 | Deleting an untracked file is judged | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-07 …" | CI engine.xml |
| REQ-IMH-08 | Snapshot directory is per-user, 0700 and not a symlink; a planted link fails closed | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-08 …" | CI engine.xml |
| REQ-IMH-09 | Engine git calls neutralise command-executing config; a repository config with a denied key is refused, and the marker script never runs | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-09 …" | CI engine.xml |
| REQ-IMH-10 | Pathspec, `--only` and `--include` commits denied; `-a` checks tracked working-tree changes | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-10 …" | CI engine.xml |
| REQ-IMH-11 | A replayed audit entry is a break | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-11 …" | CI engine.xml |
| REQ-IMH-12 | `run-tests.sh` runs `gaps --strict` last against its own results, honours `EVIDENCE_RESULTS_DIR`, and passes in one pass without touching `validation/` | content + CI | yes | — | `tests/content_acceptance_tests.py` "REQ-IMH-12 …"; `scripts/ci/run-tests.sh` gaps step → gaps.xml | CI content.xml, gaps.xml |
| REQ-IMH-13 | Adapter YAML inline comments stripped | engine (CLI unit) | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-13 …" | CI engine.xml |
| REQ-IMH-14 | A plan ID already defined by a spec is a reference; no DUPLICATE-ID | engine (CLI unit) | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-14 …" | CI engine.xml |
| REQ-IMH-15 | Temp-directory arguments count as script execution only for executing programs | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-15 …" | CI engine.xml |
| REQ-IMH-16 | `engine-tests.py -k` never crashes on skipped setup | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-16 …" (runs itself with `-k` in a subprocess) | CI engine.xml |
| REQ-IMH-17 | Re-approval appends a history entry | lifecycle | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-IMH-17 …" | CI lifecycle.xml |
| REQ-IMH-18 | Docs, governance, HANDOFF and Known issues match the shipped behaviour | content | yes | — | `tests/content_acceptance_tests.py` "REQ-IMH-18 …" | CI content.xml |
| MAN-IMH-01 | Live: two Claude sessions (or parallel subagents) in one folder produce no false violation, and the human's local `run-tests.sh` during a session changes nothing under `validation/` | manual | no | MAN-IMH-01 | — | Session note in the PR |

## Considered and rejected
- **Editing `.github/workflows/ci.yml` to set `EVIDENCE_RESULTS_DIR`.** It's change-controlled, and detecting `GITHUB_ACTIONS` in `run-tests.sh` gives the same result.
- **A separate git-config key list.** `deny_git_config_keys` already exists and is documented. One list for both the `git -c` gate and the hook's own git calls keeps them consistent.
- **Splitting now.** See Risks → Size. The split is decided at step 1 on measured size, not guessed.
- **The ADR alternatives:** see `.evidence/decisions/0001-*.md` and `0002-*.md`.
