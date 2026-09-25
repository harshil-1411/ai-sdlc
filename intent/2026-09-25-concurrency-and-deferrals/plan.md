# Plan: Concurrency-safe integrity monitor and the PILOT-58 review deferrals
Tracker: PILOT-59   From: intent/2026-09-25-concurrency-and-deferrals/spec.md   Date: 2026-09-25
Risk tier: 3. The change covers the integrity monitor and how it restores signed records, the audit log (a new attestation log, under the `**/audit/**` floor), the Bash pre-check parser, the approval route, and `verify-range` rules 2 and 4. "Any change to this framework's own gates" is Tier 3 (risk-tiering skill), and a wrong restore or attribution loses or forges regulated records. A second human approves (Harshil).

Approval is not written in this file. A human records it with `/evidence-sdlc:approve <KEY> <plan-sha>`
(or `evidence approve <KEY>` in their own terminal, or an approving review in GitHub
mode); it binds to this file's hash, so any edit after approval voids it.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

Written with evidence-sdlc disabled in `.claude/settings.json` (owner decision, 2026-09-25): no change state exists for PILOT-59 yet, and nothing here is signed. The human runs `evidence change start PILOT-59 --tier 3 --kind fix` before approving.

## Split (owner decides at approval)
**Recommendation: split.** The whole change is estimated at 1,700–2,600 changed lines [NEEDS VERIFICATION after step 1]. Its two halves share no design, so one reviewer pass cannot hold both.

| Part | REQ IDs | Files | Estimate | Version |
| --- | --- | --- | --- | --- |
| **59a, concurrency and monitor gaps** | REQ-CON-01..13, REQ-CON-24 (its part) | `monitor.py` (new), `integrity.py`, `hook.py`, `state.py`, `lifecycle.py` (the attested callers), `default-policy.json`, `hooks.json` | 1,200–1,800 | 2.5.0 |
| **59b, deferrals** | REQ-CON-14..23, REQ-CON-24 (its part) | `cmdparse.py`, `lifecycle.py` (`_approve_github`, `_check_audit`, `_check_paths`, `_owners_of`), `evidence_policy.py`, `hook.py` (`run_integrity` re-arm), `state.py` (`_merge`) | 500–800 | 2.4.0 |

- **59b merges first.** It is smaller, and REQ-CON-15 closes a live pre-check bypass.
- **Keys:** 59a keeps the key PILOT-59, and 59b needs a tracker key, proposed PILOT-65 [NEEDS VERIFICATION: key not yet allocated]. Both keep this plan document. Each PR lists the REQ IDs it proves.
- **Without the split:** one PR, version 2.4.0, and the order of work below as written.

## Files claimed
- `intent/2026-09-25-concurrency-and-deferrals/**`
- `.evidence/decisions/**`
- `plugins/evidence-sdlc/scripts/engine/monitor.py` (new)
- `plugins/evidence-sdlc/scripts/engine/integrity.py`
- `plugins/evidence-sdlc/scripts/engine/hook.py`
- `plugins/evidence-sdlc/scripts/engine/state.py`
- `plugins/evidence-sdlc/scripts/engine/lifecycle.py`
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`
- `plugins/evidence-sdlc/scripts/engine/cmdparse.py`
- `plugins/evidence-sdlc/hooks/hooks.json` (only if step 1 confirms a tool-failure hook event)
- `plugins/evidence-sdlc/policy/default-policy.json`
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`
- `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py`
- `plugins/evidence-sdlc/scripts/tests/fixtures/pilot59/**` (new: verify-range merge fixtures, a fake gh user response)
- `tests/content_acceptance_tests.py`
- `docs/gates-reference.md`
- `docs/policy-reference.md`
- `docs/managed-settings.md`
- `governance/control-mapping.md`
- `governance/supplier-audit-packet.md`
- `SECURITY.md`
- `HANDOFF.md`
- `CHANGELOG.md`
- `plugins/*/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`

Not changed: `.github/workflows/**`, `validation/**`, `scripts/ci/**`, `signing.py`, `secretscan.py`, `.claude/settings.json`, `.evidence/adapter.yml`.

## Files that change
- `plugins/evidence-sdlc/scripts/engine/monitor.py` (new):
  - `ensure_dir` (owner and mode check, REQ-CON-01);
  - `lock`;
  - `next_seq`;
  - `open_window` / `close_window` / `load_lease`;
  - `windows_overlapping`, `expired_windows`, `attested_since`, `last_post` / `write_last_post` (REQ-CON-02..05, 07, 09).
- `plugins/evidence-sdlc/scripts/engine/integrity.py`:
  - `_snap_rel` / `_snap_path` move to the monitor directory, with a legacy read fallback (REQ-CON-01);
  - `snapshot` adds `seq`, `prev`, the lease binding, the realpath `root` and `ENGINE_RECORDS` (REQ-CON-03, 09);
  - `check`:
    - takes `group` and `lease`;
    - the preamble adds pairing (REQ-CON-03) and the root switch (REQ-CON-13);
    - step 1 gains an engine-record attestation branch before the 2.1 restore (REQ-CON-07);
    - step 3 gains declared-write explanation and group judging (REQ-CON-08);
  - `_hash` and `_dirty` (REQ-CON-12);
  - `_git_dir_id` and `_extras` fail closed (REQ-CON-23).
- `plugins/evidence-sdlc/scripts/engine/hook.py`:
  - `run_pre`: lock, deferred checks, `tool-start`, lease, `monitor-busy` / `monitor-unpaired` / `monitor-dir-unsafe` (REQ-CON-02, 04, 05, 11);
  - `run_post`: lease close for the edit tools, `tool_use_id` on post entries;
  - `run_integrity`: the snapshot root context, group judges, dedupe, `last-post`, and the re-armed watchdog (REQ-CON-08, 09, 13, 14).
- `plugins/evidence-sdlc/scripts/engine/state.py`:
  - `_dir_fd` and `write_file` take a `mode`;
  - new `attested_write`;
  - `save_state` and `write_violations` use it;
  - `record_violations` adds `attribution`, `windows` and the content-hash dedupe;
  - `audit_verify_lines` treats `attestations.jsonl` as shared by name and warns on an unpaired `tool-start`;
  - `_attr_source` and `current_branch` go through the sweep (REQ-CON-23);
  - `_merge` gains rules for the three `monitor_*` keys and `approval.github_identities`;
  - `ENGINE_VERSION`.
- `plugins/evidence-sdlc/scripts/engine/lifecycle.py`:
  - `write_approval`, `_clear_violations`, and `cmd_change` (`set-tier`, `release`, `failing-test` `fix_base`) take the lock and use `attested_write` (REQ-CON-06, 10, 23);
  - `cmd_change start` records `created_by_github` (REQ-CON-16);
  - `_approve_github` adds the creator rule and `creator_login` (REQ-CON-16);
  - `approve_from_prompt` takes the lock (REQ-CON-10);
  - `_check_audit` gains `_ordered_subseq` and `_SHARED_LOG` (REQ-CON-17, 18);
  - `_check_paths` (REQ-CON-19);
  - `_owners_of` (REQ-CON-21).
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`:
  - `check_write`: `tier3-same-person` for method `github` (REQ-CON-16), and the advisory note for `.evidence/context|decisions` (REQ-CON-20);
  - `_commit_bypass`: abbreviation resolution (REQ-CON-22);
  - the fallback at `:467` (REQ-CON-23).
- `plugins/evidence-sdlc/scripts/engine/cmdparse.py`: new `_split_lines`, the `_HEREDOC` regex and `_strip_heredocs` `repl`, and `split_simple` (REQ-CON-15).
- `plugins/evidence-sdlc/policy/default-policy.json`: `monitor_window_ttl_seconds`, `monitor_background_ttl_seconds`, `monitor_lock_wait_seconds`, `approval.github_identities`.
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`: new `suite_pilot59`, with a case per engine Proof row. It uses PILOT-60's `--suite` harness, and a test clock through `EVIDENCE_TEST_CLOCK` (read only when `EVIDENCE_TEST_MODE=1`, which the harness sets; the engine test for REQ-CON-05 proves an unset flag ignores it).
- `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py`: new `verify_range_59_tests()` (REQ-CON-17..19, 21) and `approve_github_59_tests()` (REQ-CON-16).
- `plugins/evidence-sdlc/scripts/tests/fixtures/pilot59/`: merge-shape repositories built by script, and `gh-user.json`.
- `tests/content_acceptance_tests.py`: REQ-CON-24.
- Docs and release (REQ-CON-24):
  - `docs/gates-reference.md`: windows, leases, attestation, overlap violations, the new rules (`monitor-busy`, `monitor-unpaired`, `monitor-dir-unsafe`, `integrity-lease-*`, `integrity-chain-broken`), and the parser;
  - `docs/policy-reference.md`: the new keys and their merge rules;
  - `docs/managed-settings.md`: `approval.github_identities`;
  - `SECURITY.md`, `governance/control-mapping.md` and `governance/supplier-audit-packet.md`: the concurrency known issue removed, and attestation described;
  - `HANDOFF.md`;
  - `CHANGELOG.md` `## 2.4.0` (or 2.4.0 and 2.5.0 if split);
  - versions in `plugins/evidence-sdlc/.claude-plugin/plugin.json`, `plugins/evidence-discovery/.claude-plugin/plugin.json`, `plugins/evidence-quality/.claude-plugin/plugin.json`, `plugins/evidence-compliance/.claude-plugin/plugin.json`, `plugins/evidence-integrations/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
- `.evidence/decisions/0006-monitor-windows-attested-writes-chained-snapshots.md` (new; written with this plan).

## Coordination
**Merge order: PILOT-62 → PILOT-60 → PILOT-59, with a rebase onto `main` after each merge.**
- PILOT-62 (`feat/PILOT-62-local-layer-advisory`, plan at `61667a2`) ships 2.2.0.
- PILOT-60 (`fix/PILOT-60-usability`, plan at `a14382c`) ships 2.3.0.
- PILOT-59 ships **2.4.0**. If split, 59b ships 2.4.0 and 59a 2.5.0. If the owner reorders the merges, the change that merges later takes the higher version.

**Before PILOT-60 merges,** PILOT-59 does only work in files no other change claims:
- `cmdparse.py`, which PILOT-60 explicitly leaves to PILOT-59;
- the new `monitor.py`;
- `fixtures/pilot59/**`;
- the ADR.

Its failing tests are drafted in a scratch branch and moved into `suite_pilot59` after the rebase.

**Shared files, and the functions each change edits:**

| File | PILOT-62 edits | PILOT-60 edits | PILOT-59 edits |
| --- | --- | --- | --- |
| `integrity.py` | `check` step 1 and 1a (verified undo, `AUTO_RESOLVABLE`), `_permission_grant` → `_local_settings_change`, `_extras` per-kind values and step 1b, new `_not_user_writable`, `_claude_json_projection` | none | `_snap_rel`/`_snap_path`, `snapshot`, the `check` preamble, a new engine-record branch in `check` step 1 (**same block as PILOT-62**), `check` step 3, `_hash`, `_dirty`, `_git_dir_id`, `_extras` git-failure line (**same function as PILOT-62**) |
| `hook.py` | `run_integrity` (cap split, `config-change` / `user-config-changed` events, per-class messages) | none | `run_pre`, `run_post`, `run_integrity` (**same function as PILOT-62**: context switch, group judges, dedupe, re-arm) |
| `state.py` | `record_violations` (`resolved` fields), new `auto_resolved_count`, two `_merge` rules, `ENGINE_VERSION` | `check_git_config`, new `ENGINE_ALWAYS_REFUSED` / `_engine_ignored`, one `_merge` rule, `ENGINE_VERSION` | `_dir_fd`, `write_file`, new `attested_write`, `save_state`, `write_violations`, `record_violations` (**same function as PILOT-62**), `audit_verify_lines`, `_attr_source`, `current_branch`, four `_merge` rules, `ENGINE_VERSION` |
| `lifecycle.py` | `_record_transition` (rule 5) | none | `write_approval`, `_clear_violations`, `cmd_change`, `approve_from_prompt`, `_approve_github`, `_check_audit`, `_check_paths`, `_owners_of`; **not** `_record_transition` |
| `evidence_policy.py` | `check_write` `tier3-auto-mode` branch, `_check_gh`, new `_ci_gate` | `check_bash` argument loop, `_check_script`, new temp helpers | `check_write` `tier3-same-person` branch (**adjacent to PILOT-62's branch**) and a new advisory note, `_commit_bypass`, the `:467` fallback in the commit-message check |
| `cmdparse.py` | none | none (left to PILOT-59) | `_split_lines`, `_HEREDOC`, `_strip_heredocs`, `split_simple` |
| `default-policy.json` | ten new keys | `git_config_engine_ignored` | four new keys |
| `engine-tests.py` | `suite_pilot62` | harness (`case`, `SUITES`, `--suite`), `suite_pilot60` | `suite_pilot59` (on PILOT-60's harness), appended to `SUITES` |
| `cli-lifecycle-tests.py` | `verify-range` fixtures (REQ-LLA-04) | `gaps_tests()` | `verify_range_59_tests()`, `approve_github_59_tests()` |
| docs, governance, SECURITY, HANDOFF, CHANGELOG, versions | 2.2.0 | 2.3.0 | 2.4.0 |

**Composition rules after the rebase:**
1. **PILOT-62's verified undo** applies to every restore PILOT-59 still performs:
   - the chained-target restore of engine-owned records;
   - the 2.1 restore of other control-plane files.

   An engine-owned record kept because it is attested is not a violation at all, so it never reaches the auto-resolve cap.
2. **PILOT-62's per-session auto-resolve cap** counts a group-attributed resolved entry against the session whose post recorded it.
3. **PILOT-62's `_local_settings_change`** stays the rule for `.claude/settings.local.json`. PILOT-59 does not touch it.
4. **PILOT-60's `_TEMP_DATA_PROGS` rule** reads `cmdparse.writes_of`, whose behaviour REQ-CON-15 changes only for multi-line commands. PILOT-60's REQ-USA-07/08 cases are re-run after the rebase.
5. Rebase conflicts are expected in `integrity.check`, `hook.run_integrity`, `state.record_violations`, `_merge`, `check_write`, `default-policy.json`, the `SUITES` list and the docs. Resolve them by keeping every side's behaviour, then rerun all three changes' suites.

## Order of work
1. **Verify and write the failing tests.**
   - Confirm from Claude Code's hook documentation, and a live trace in a scratch repository, whether PostToolUse fires for:
     - an interrupted Bash call;
     - a failed tool call;
     - `run_in_background: true` (at launch or at the end).

     Also confirm whether a failure event exists, and whether hooks see the same `TMPDIR` as the human terminal. Record the results here and adjust REQ-CON-05's TTLs.
   - Confirm git's handling of `git commit --o` (REQ-CON-22).
   - `grep` the tests for:
     - cases that assume the `$TMPDIR` snapshot path;
     - base-first shared-log merge fixtures;
     - heredoc-then-command cases.

     List them here.
   - Write every Proof row's test and run it to record why it fails. Engine cases go in `suite_pilot59` after the PILOT-60 rebase; before it, they go in a scratch file.
   - Ask the maintainer for review nits 2–5.
2. **59b first (or the 59b steps, if not split). Before PILOT-60 merges:**
   - REQ-CON-15 in `cmdparse.py`;
   - run `engine-tests.py` in full (background, about 8 minutes), because every Bash rule reads `split_simple`.
3. **After PILOT-62 and PILOT-60 merge, rebase.** Then:
   - REQ-CON-14, 16, 20, 22 and 23 in `hook.py`, `lifecycle.py`, `evidence_policy.py` and `state.py`;
   - REQ-CON-17, 18, 19 and 21 in `lifecycle.py`, with the `verify-range` fixtures;
   - run the engine suite, then `cli-lifecycle-tests.py verify-range`.
   - **Precondition:** the human has resolved the uncommitted working-tree edit of `default-policy.json` and removed `default-policy.json.bak`. If not, stop and ask. Never stage, overwrite or revert them.
4. **CHECKPOINT (59b):**
   - re-read spec.md;
   - run the full engine, lifecycle and content suites;
   - run the **security-reviewer on steps 2–3 alone**, and wait for it to finish.

   If split, 59b's docs (REQ-CON-24, its part), CHANGELOG 2.4.0 and versions follow, then its reviews (step 10) and PR.
5. **59a, engine helpers before callers.** Hooks read the engine live, and a NameError locks the session out.
   - Add `monitor.py`, `st.attested_write`, the `mode` parameters, and `ENGINE_RECORDS`, each unused.
   - Run the engine suite.
6. REQ-CON-01, 12, 13 (directory, special files, root). Then REQ-CON-11 (`tool-start`). Run the engine suite after each.
7. REQ-CON-06, 10 (attested writes and locked human writes in `state.py` / `lifecycle.py`). Then REQ-CON-02, 03, 04 (leases and pairing in `hook.run_pre` / `run_post` / `integrity.check`). Run the engine suite after each.
8. **CHECKPOINT (59a):**
   - re-read spec.md and ADR-0006;
   - run the full engine suite;
   - run `evidence audit verify` on this repository's logs;
   - run the **security-reviewer on steps 5–7 alone**, and wait for it to finish.
9. REQ-CON-07, 08, 09, 05 (attestation judging, overlap attribution, chained snapshots, deferred checks). Run the engine suite, then the thread-based concurrency cases 10 times in a loop to catch flakes.
10. REQ-CON-24: ADR-0006 status note, docs, governance, SECURITY, HANDOFF, CHANGELOG, versions. Run the engine, lifecycle, `verify-range` fixture and content suites directly (no `JUNIT_OUT`). Confirm nothing under `validation/` changed.
11. Reviewers one at a time, with no edits during a run: code-reviewer, security-reviewer, then the verifier last. Only a new Critical or High reopens the code; everything else is listed for a later change.
12. Commit and push (`git add` and `git commit` in separate calls; `-m` flags, no heredoc). The maintainer opens the PR from their own account; Harshil reviews; the human merges and releases.
13. **Live checks after the merge, human-run:**
    - MAN-CON-01: three parallel review subagents with main-session edits;
    - MAN-CON-02: `clear-violations` mid-call.

    **Owner actions:**
    - allocate the 59b key if split;
    - set `approval.github_identities` in the org policy for every Tier 3 change creator;
    - confirm the lock-wait and TTL defaults.

Steps 2 and 5 are independent (different files). Steps 6 and 7 wait for the rebase in step 3.

## Mid-flight checkpoint (Tier 2/3)
Steps 4 and 8.

## Reuse decisions
- **Leases, the sequence counter, `last-post.json` and attestations** are signed with `signing.sign` and written with `st.write_file`, which is no-follow and atomic. No new crypto, and no new subprocess (the REQ-IMH-22 allow-list is unchanged).
- **The attestation log** is an ordinary audit log (`audit_append` with its `flock`, hash chain and signatures). It is verified by `audit_verify` and `verify-range` rule 4, like the other shared logs.
- **Group judging** reuses `ep.check_write` through the existing `judge` closure, once per window context.
- **The restore** of engine-owned records reuses `st.write_file`. Only the target changes, from the pre snapshot to the chained attested content.
- **The parser fix** stays inside `split_simple`, so every caller (`check_bash`, `lifecycle_call`, `cli_writes`, PILOT-60's temp rule) benefits unchanged.
- **The creator check** reuses `st.run_gh`, which pins the repository and scrubs the environment.

## Risks
- **Steps 6–9 can lock this session.** Hooks read `integrity.py`, `hook.py`, `state.py` and `monitor.py` live. Mitigation: helpers first, small edits, and the engine suite after each step. Rollback: `git checkout -- <file>` by the human.
- **A lock bug denies every call.** Mitigation: the bounded wait, the `monitor-busy` message, and a test that a lock holder killed with SIGKILL frees the lock (`flock` is released by the kernel).
- **Over-broad explanation** would launder writes. Mitigation: only paths in a pre-allowed `declared_writes` are explained, and each laundering shape has a negative test.
- **Concurrency tests are flaky.** Mitigation: the tests drive the interleavings explicitly (pre A, pre B, write, post B, post A) through `run_hook`. Only REQ-CON-10 uses threads, and it runs 10 times in step 9.
- **Upgrade mid-session:** a pre from 2.3 and a post from 2.4. Mitigation: the legacy snapshot fallback (REQ-CON-01), for one release.
- **Rebase conflicts** with PILOT-62 and PILOT-60 (see "Coordination").
- **Size:** see "Split".

## Proof

| REQ ID | Requirement | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-CON-01 | The monitor directory is 0700/0600 and owner-checked; an unsafe directory denies; a legacy snapshot pairs once | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-01 …" (modes; 0777 dir → `monitor-dir-unsafe`; symlinked dir → deny; legacy tmp snapshot → no violation) | CI engine.xml |
| REQ-CON-02 | Every allowed Bash and edit-tool call registers a signed lease with the listed fields; the post closes it; old closed leases are pruned | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-02 …" | CI engine.xml |
| REQ-CON-03 | A post pairs with its own lease and snapshot by `tool_use_id`; a swapped snapshot is `integrity-snapshot-replayed`; a missing `tool_use_id` with another window open is denied | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-03 …" (two overlapping calls in one session; A's snapshot copied to B; no id plus an open window → `monitor-unpaired`; no id alone → allowed) | CI engine.xml |
| REQ-CON-04 | Negative: a missing, altered or forged lease, or a lock timeout, fails closed; unsigned leases make nothing acceptable | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-04 …" (lease deleted; lease edited; forged foreign lease; held `flock` → `monitor-busy` and `integrity-lock-timeout`; unsigned forged lease) | CI engine.xml |
| REQ-CON-05 | An expired window is checked by the next critical section and attributed to the expired call; its missing snapshot is a violation; the test clock needs the test flag | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-05 …" (`EVIDENCE_TEST_CLOCK`; deferred check records the unparsed write against the expired window; snapshot removed → `integrity-snapshot-missing`; clock ignored without `EVIDENCE_TEST_MODE`) | CI engine.xml |
| REQ-CON-06 | Engine-owned record writes append a signed, chained attestation before the write; the chain verifies; a bad signature fails | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-06 …" | CI engine.xml |
| REQ-CON-07 | Attested changes in the window are kept (another call's violations, a human's clear or approval); a replayed older signed record or an unattested write is restored; unsigned is recorded | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-07 …" (A/B overlap keeps B's entry and session; mid-call `clear-violations` stays cleared; mid-call `approve` kept; negative: replayed `approval.json` → restored; unattested signed record → restored; unsigned → recorded) | CI engine.xml |
| REQ-CON-08 | Declared writes of overlapping windows are explained; unexplained changes are judged under every window and recorded once with the group; laundering is refused | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-08 …" (reviewer `ls` versus main Edit → no violation; shared unparsed write → one entry with both windows; negative: reviewer's unparsed write with nothing declared → violation; only the declared path explained) | CI engine.xml |
| REQ-CON-09 | Chained snapshots: a between-calls change is logged, not charged; a missing or altered `last-post` is `integrity-chain-broken`; a background window's later write is attributed to it | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-09 …" | CI engine.xml |
| REQ-CON-10 | Posts and human record writes are serialised by the lock; concurrent posts lose no entries; a human write refuses while the lock is held | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-10 …" (two threaded posts → both entries; `clear-violations` under a held lock → refused, then succeeds) | CI engine.xml |
| REQ-CON-11 | Allowed calls write `tool-start` before running; post entries carry `tool_use_id`; a lone `tool-start` is an `unpaired` warning; an unwritable log denies | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-11 …" | CI engine.xml |
| REQ-CON-12 | FIFOs, devices and links neither stall nor get followed, and are still detected as changes | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-12 …" (`mkfifo`, a `/dev/zero` link, a `junk -> /` link; pre and post each under 5 s) | CI engine.xml |
| REQ-CON-13 | The post checks the snapshot's root, not the post `cwd`, and logs `root-moved` | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-13 …" (two scratch repositories) | CI engine.xml |
| REQ-CON-14 | After a post-hook timeout, the watchdog is re-armed, and the hook still returns within 30 s with the audit entry | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-14 …" (stubbed slow `check` and `record_violations`) | CI engine.xml |
| REQ-CON-15 | Commands after a newline or a heredoc's operator line are parsed; here-strings are not heredocs; continuations join | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-15 …" (denied: `echo hi⏎touch src/auth/login.py`, `cat <<EOF \| sh⏎…`, `cat <<EOF && touch …`; allowed: heredoc then `git status`, heredoc commit then `git status`; `<<<` then `rm` seen; `echo a \⏎b` one command) | CI engine.xml |
| REQ-CON-16 | A GitHub approval by the creator (captured login or org map) is refused; another approver is accepted and `creator_login` recorded; Tier 3 with no known creator login is refused; `tier3-same-person` covers `github` | CLI | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-CON-16 …" (fake `gh`, `fixtures/pilot59/gh-user.json`) and `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-16 tier3-same-person github" | CI lifecycle.xml, engine.xml |
| REQ-CON-17 | Rule 4 containment is ordered: reordered log lines fail; append-only passes | CLI | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-CON-17 …" | CI lifecycle.xml |
| REQ-CON-18 | A shared log merged with the base's lines first passes; a merged line from neither parent fails; one session's log on both sides fails with the rebase message | CLI | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-CON-18 …" (fixtures under `fixtures/pilot59/`) | CI lifecycle.xml |
| REQ-CON-19 | Non-record files under `.evidence/changes/`, `.evidence/violations/` and `.evidence/audit/` must be claimed; records and session logs stay exempt | CLI | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-CON-19 …" | CI lifecycle.xml |
| REQ-CON-20 | An unclaimed `.evidence/decisions/` or `.evidence/context/` edit stays allowed locally with an advisory note; a claimed one has no note | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-20 …" | CI engine.xml |
| REQ-CON-21 | Slashless CODEOWNERS patterns match at any depth; anchored patterns do not | CLI | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-CON-21 …" | CI lifecycle.xml |
| REQ-CON-22 | Abbreviated long options (`--o`, `--onl`, `--inc`) are resolved and denied as `commit-bypass`; a plain `-m` commit is allowed | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-22 …" | CI engine.xml |
| REQ-CON-23 | Git-failure fallbacks fail closed (`fix_base` empty → refused; `_extras` → `git-unavailable`); the full list is in the PR | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-CON-23 …" | CI engine.xml |
| REQ-CON-24 | ADR-0006, docs, governance, SECURITY, HANDOFF, CHANGELOG 2.4.0 and versions match; the unsupported merge shape and the owner actions are stated | content | yes | — | `tests/content_acceptance_tests.py` "REQ-CON-24 …" | CI content.xml |
| REQ-CON-08 (live) | Live, on this repository after the merge: three parallel review subagents (Bash reads), while the main session edits claimed files, produce no violation. `evidence audit verify` shows paired `tool-start`/`tool` entries | manual | no | MAN-CON-01 | — | Session audit log excerpt in the release note |
| REQ-CON-07 (live) | Live: the human runs `evidence change clear-violations` in their own terminal while an agent Bash call is running. After the post, `evidence change status` shows no open violations | manual | no | MAN-CON-02 | — | Terminal output pasted in the release note |

## Considered and rejected
- **One change without a split.** It is allowed if the owner prefers (see "Split"), but it is not recommended at this size.
- **ADR-0001's design, serialising whole calls, and charging every overlapping call** (spec, "Rejected alternatives"; ADR-0006).
- **Supporting one session's log merged on both sides.** Rebase avoids it, and it would need fork-tolerant chains.
- **Loosening `verify-range` for `.evidence/context/` and `.evidence/decisions/`.** It would weaken what merges. The local advisory note is chosen instead (REQ-CON-20).
